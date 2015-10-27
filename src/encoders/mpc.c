#include "../mpc/datatypes.h"
#include "../libmpcpsy/libmpcpsy.h"
#include "../libmpcenc/libmpcenc.h"
#include "../pcmreader.h"

// Utility macros
#ifndef MIN
#define MIN(X,Y) (((X) < (Y)) ? (X) : (Y))
#endif

// Version macros for encoder info block
#define MPCENC_MAJOR 1
#define MPCENC_MINOR 30
#define MPCENC_BUILD 1

typedef enum {
    ENCODE_OK,
    ERR_INVALID_ARGUMENT,
    ERR_UNSUPPORTED_SAMPLE_RATE,
    ERR_UNSUPPORTED_CHANNELS,
    ERR_UNSUPPORTED_BITS_PER_SAMPLE,
    ERR_FILE_OPEN,
    ERR_FILE_READ
} result_t;

static void fill_float(float *p, float f, unsigned n) {
    unsigned i;
    for( i = 0 ; i < n ; ++i ) {
        p[i] = f;
    }
}

static int
read_pcm_samples(struct PCMReader *pcmreader,
                 PCMDataTyp *out,
                 unsigned samples,
                 int *silence) {
    // Special multipliers used to adjust left / right.
    const float DENORMAL_FIX_LEFT = 32.0f * 1024.0f / 16777216.0f;
    const float DENORMAL_FIX_RIGHT = DENORMAL_FIX_LEFT * 0.5f;

    int buffer[samples * pcmreader->channels];
    unsigned samples_read;
    unsigned i;
    float *l = out->L + CENTER;
    float *r = out->R + CENTER;
    float *m = out->M + CENTER;
    float *s = out->S + CENTER;

    // read PCM samples.
    if((samples_read = pcmreader->read(pcmreader, samples, buffer)) == 0) {
        return -1;
    }

    // check for silence (all null samples)
    silence[0] = 1;
    for( i = 0 ; i < samples_read * pcmreader->channels ; ++i ) {
        if(buffer[i]) {
            silence[0] = 0;
            break;
        }
    }

    // pad buffer with null samples if it wasn't filled completely
    memset(&buffer[samples_read * pcmreader->channels],
           0,
           (samples - samples_read) * pcmreader->channels * sizeof(int));

    // TODO: support conversion from bits_per_samples other than 16?
    switch(pcmreader->channels) {
        case 1:
            for( i = 0 ; i < samples ; ++i ) {
                l[i] = buffer[i] * DENORMAL_FIX_LEFT;
                l[i] = buffer[i] * DENORMAL_FIX_RIGHT;
                m[i] = (l[i] + r[i]) * 0.5f;
                s[i] = (l[i] - r[i]) * 0.5f;
            }
            break;

        case 2:
            for( i = 0 ; i < samples ; ++i ) {
                l[i] = buffer[i * 2 + 0] * DENORMAL_FIX_LEFT;
                r[i] = buffer[i * 2 + 1] * DENORMAL_FIX_RIGHT;
                m[i] = (l[i] + r[i]) * 0.5f;
                s[i] = (l[i] - r[i]) * 0.5f;
            }
            break;
    }

    return samples_read;
}

static result_t
encode_mpc_file(char *filename,
                struct PCMReader *pcmreader,
                float quality,
                unsigned total_pcm_samples)
{
    // Constant configuration values (same defaults as reference encoder)
    const unsigned int FramesBlockPwr = 6;
    const unsigned int SeekDistance = 1;

    FILE *f;
    PsyModel m;
    mpc_encoder_t e;
    int si_size;
    PCMDataTyp Main;
    unsigned samples_read;
    int silence;
    unsigned total_samples_read;
    SubbandFloatTyp X[32];

    // check arguments
    if(filename == NULL    ||
       filename[0] == '\0' ||
       pcmreader == NULL   ||
       quality < 00.0f     ||
       quality > 10.0f     ||
       total_pcm_samples < 1) {
        return ERR_INVALID_ARGUMENT;
    }

    // Check for supported sample rates.
    switch(pcmreader->sample_rate) {
        case 32000:
        case 37800:
        case 44100:
        case 48000: break;
        default:    return ERR_UNSUPPORTED_SAMPLE_RATE;
    }

    // Check for supported channels.
    switch(pcmreader->channels) {
        case 1:
        case 2:  break;
        default: return ERR_UNSUPPORTED_CHANNELS;
    }

    // Check for supported bits per sample.
    // TODO: add 8-32 bit support? the reference encoder supports it.
    switch(pcmreader->bits_per_sample) {
        case 16: break;
        default: return ERR_UNSUPPORTED_BITS_PER_SAMPLE;
    }

    // open output file for writing
    if((f = fopen(filename, "wb")) == NULL) {
        return ERR_FILE_OPEN;
    }

    // Initialize encoder objects.
    m.SCF_Index_L = e.SCF_Index_L;
    m.SCF_Index_R = e.SCF_Index_R;
    Init_Psychoakustik(&m);
    m.SampleFreq = pcmreader->sample_rate;
    SetQualityParams(&m, quality);
    mpc_encoder_init(&e, total_pcm_samples, FramesBlockPwr, SeekDistance);
    Init_Psychoakustiktabellen(&m);
    e.outputFile = f;
    e.MS_Channelmode = m.MS_Channelmode;
    e.seek_ref = ftell(f);

    // write stream header block
    writeMagic(&e);
    writeStreamInfo(&e,
                    m.Max_Band,
                    m.MS_Channelmode > 0,
                    total_pcm_samples,
                    0,
                    m.SampleFreq,
                    pcmreader->channels);
    si_size = writeBlock(&e, "SH", MPC_TRUE, 0);

    // write replay gain block
    writeGainInfo(&e, 0, 0, 0, 0);
    writeBlock(&e, "RG", MPC_FALSE, 0);

    // write encoder information block
    writeEncoderInfo(&e,
                     m.FullQual,
                     m.PNS > 0,
                     MPCENC_MAJOR,
                     MPCENC_MINOR,
                     MPCENC_BUILD);
    writeBlock(&e, "EI", MPC_FALSE, 0);

    // reserve space for seek offset.
    e.seek_ptr = ftell(f);
    writeBits(&e, 0, 16);
    writeBits(&e, 0, 24);
    writeBlock(&e, "SO", MPC_FALSE, 0);

    // Read the first audio block. At least one will be read.
    memset(&Main, 0, sizeof(Main));
    samples_read = read_pcm_samples(pcmreader,
                                    &Main,
                                    MIN(BLOCK, total_pcm_samples),
                                    &silence);
    total_samples_read = samples_read;

    // Check for read error.
    if(samples_read == -1) {
        return ERR_FILE_READ;
    }

    if(samples_read > 0) {
        fill_float(Main.L, Main.L[CENTER], CENTER);
        fill_float(Main.R, Main.R[CENTER], CENTER);
        fill_float(Main.M, Main.M[CENTER], CENTER);
        fill_float(Main.S, Main.S[CENTER], CENTER);
    }

    Analyse_Init(Main.L[CENTER], Main.R[CENTER], X, m.Max_Band);

    return ENCODE_OK;
}

#ifndef STANDALONE
PyObject*
encoders_encode_mpc(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    Py_INCREF(Py_None);
    return Py_None;
}
#endif

#ifdef STANDALONE
int main(int argc, char *argv[])
{
    return 0;
}
#endif
