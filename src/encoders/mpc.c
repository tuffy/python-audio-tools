#include "../mpc/datatypes.h"
#include "../libmpcpsy/libmpcpsy.h"
#include "../libmpcenc/libmpcenc.h"
#include "../pcmreader.h"

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
    ERR_FILE_OPEN
} result_t;

static int
read_pcm_samples(struct PCMReader *pcmreader,
                 PCMDataTyp *out,
                 unsigned samples,
                 int *silence) {
    int buffer[samples * pcmreader->channels];
    unsigned samples_read;
    unsigned i;

    // read PCM samples.
    if((samples_read = pcmreader->read(pcmreader, samples, buffer)) == 0) {
        return -1;
    }

    return -1;
}

static result_t
encode_mpc_file(char *filename,
                struct PCMReader *pcmreader,
                float quality,
                long long total_pcm_frames)
{
    // Constant configuration values (same defaults as reference encoder)
    const unsigned int FramesBlockPwr = 6;
    const unsigned int SeekDistance = 1;

    FILE *f;
    PsyModel m;
    mpc_encoder_t e;
    int si_size;

    if(filename == NULL    ||
       filename[0] == '\0' ||
       pcmreader == NULL   ||
       quality < 00.0f     ||
       quality > 10.0f     ||
       total_pcm_frames < 1) {
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

    if((f = fopen(filename, "wb")) == NULL) {
        return ERR_FILE_OPEN;
    }

    // Initialize encoder objects.
    m.SCF_Index_L = e.SCF_Index_L;
    m.SCF_Index_R = e.SCF_Index_R;
    Init_Psychoakustik(&m);
    m.SampleFreq = pcmreader->sample_rate;
    SetQualityParams(&m, quality);
    mpc_encoder_init(&e, total_pcm_frames, FramesBlockPwr, SeekDistance);
    Init_Psychoakustiktabellen(&m);
    e.outputFile = f;
    e.MS_Channelmode = m.MS_Channelmode;
    e.seek_ref = ftell(f);

    // write stream header block
    writeMagic(&e);
    writeStreamInfo(&e,
                    m.Max_Band,
                    m.MS_Channelmode > 0,
                    total_pcm_frames,
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
