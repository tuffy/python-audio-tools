#include "../libmpcpsy/libmpcpsy.h"
#include "../libmpcenc/libmpcenc.h"
#include "../pcmreader.h"

typedef enum {
    ENCODE_OK,
    ERR_UNSUPPORTED_SAMPLE_RATE,
    ERR_UNSUPPORTED_CHANNELS,
    ERR_UNSUPPORTED_BITS_PER_SAMPLE
} result_t;

static result_t
encode_mpc_file(char *filename,
                struct PCMReader *pcmreader,
                float quality,
                long long total_pcm_frames)
{
    // Constant configuration values (same defaults as reference encoder)
    const unsigned int FramesBlockPwr = 6;
    const unsigned int SeekDistance = 1;

    PsyModel m;
    mpc_encoder_t e;

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

    // Initialize encoder objects.
    m.SCF_Index_L = e.SCF_Index_L;
    m.SCF_Index_R = e.SCF_Index_R;
    Init_Psychoakustik(&m);
    SetQualityParams(&m, quality);
    mpc_encoder_init(&e, total_pcm_frames, FramesBlockPwr, SeekDistance);
    Init_Psychoakustiktabellen(&m);

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
