#include "core_audio.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger and the mpg123 project
 initially written by Guillaume Outters
 modified by Nicholas J Humfrey to use SFIFO code
 modified by Taihei Monma to use AudioUnit and AudioConverter APIs
 further modified by Brian Langenberger for use in Python Audio Tools

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

PyObject*
CoreAudio_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    output_CoreAudio *self;

    self = (output_CoreAudio *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
CoreAudio_dealloc(output_CoreAudio *self) {
    /*additional memory deallocation here*/
    if (!self->closed) {
        self->ao->flush(self->ao);
        self->ao->close(self->ao);
    }

    if (self->ao != NULL) {
        self->ao->deinit(self->ao);
        free(self->ao);
    }

    self->ob_type->tp_free((PyObject*)self);
}

int
CoreAudio_init(output_CoreAudio *self, PyObject *args, PyObject *kwds) {
    long sample_rate;
    int channels;
    int channel_mask;
    int bits_per_sample;

    self->ao = NULL;
    self->closed = 1;

    if (!PyArg_ParseTuple(args, "liii",
                          &sample_rate,
                          &channels,
                          &channel_mask,
                          &bits_per_sample))
        return -1;

    if ((bits_per_sample != 8) &&
        (bits_per_sample != 16) &&
        (bits_per_sample != 24)) {
        PyErr_SetString(PyExc_ValueError,
                        "bits_per_sample must be 8, 16 or 24");
        return -1;
    }

    self->ao = malloc(sizeof(audio_output_t));
    if (init_coreaudio(self->ao,
                       sample_rate,
                       channels,
                       bits_per_sample / 8,
                       1)) {
        PyErr_SetString(PyExc_ValueError,
                        "error initializing CoreAudio");
        return -1;
    }

    if (self->ao->open(self->ao)) {
        PyErr_SetString(PyExc_ValueError,
                        "error opening CoreAudio");
        return -1;
    } else {
        self->closed = 0;
    }

    return 0;
}

static PyObject* CoreAudio_play(output_CoreAudio *self, PyObject *args)
{
    unsigned char* buffer;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t buffer_size;
#else
    int buffer_size;
#endif
    int write_result;

    if (!PyArg_ParseTuple(args, "s#", &buffer, &buffer_size))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    write_result = self->ao->write(self->ao, buffer, (int)buffer_size);
    Py_END_ALLOW_THREADS

    if (write_result == -1) {
        PyErr_SetString(PyExc_ValueError,
                        "error writing data to CoreAudio");
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject* CoreAudio_flush(output_CoreAudio *self, PyObject *args)
{
    /*FIXME - ensure pending samples are played to output*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* CoreAudio_close(output_CoreAudio *self, PyObject *args)
{
    if (!self->closed) {
        self->ao->flush(self->ao);
        self->ao->close(self->ao);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static int init_coreaudio(audio_output_t* ao,
                          long sample_rate,
                          int channels,
                          int bytes_per_sample,
                          int signed_samples)
{
    if (ao==NULL) return -1;

    /* Set callbacks */
    ao->open = open_coreaudio;
    ao->flush = flush_coreaudio;
    ao->write = write_coreaudio;
    ao->close = close_coreaudio;
    ao->deinit = deinit_coreaudio;

    ao->rate = sample_rate;
    ao->channels = channels;
    ao->bytes_per_sample = bytes_per_sample;
    ao->signed_samples = signed_samples;

    /* Allocate memory for data structure */
    ao->userptr = malloc( sizeof( mpg123_coreaudio_t ) );
    if (ao->userptr==NULL) {
        return -1;
    }
    memset( ao->userptr, 0, sizeof(mpg123_coreaudio_t) );

    /* Success */
    return 0;
}

static int open_coreaudio(audio_output_t *ao)
{
    mpg123_coreaudio_t* ca = (mpg123_coreaudio_t*)ao->userptr;
    UInt32 size;
    ComponentDescription desc;
    Component comp;
    AudioStreamBasicDescription inFormat;
    AudioStreamBasicDescription outFormat;
    AURenderCallbackStruct  renderCallback;
    Boolean outWritable;

    /* Initialize our environment */
    ca->play = 0;
    ca->buffer = NULL;
    ca->buffer_size = 0;
    ca->last_buffer = 0;
    ca->play_done = 0;
    ca->decode_done = 0;


    /* Get the default audio output unit */
    desc.componentType = kAudioUnitType_Output;
    desc.componentSubType = kAudioUnitSubType_DefaultOutput;
    desc.componentManufacturer = kAudioUnitManufacturer_Apple;
    desc.componentFlags = 0;
    desc.componentFlagsMask = 0;
    comp = FindNextComponent(NULL, &desc);
    if(comp == NULL) {
        return -1;
    }

    if(OpenAComponent(comp, &(ca->outputUnit)))  {
        return -1;
    }

    if(AudioUnitInitialize(ca->outputUnit)) {
        return -1;
    }

    /* Specify the output PCM format */
    AudioUnitGetPropertyInfo(ca->outputUnit,
                             kAudioUnitProperty_StreamFormat,
                             kAudioUnitScope_Output,
                             0,
                             &size,
                             &outWritable);
    if(AudioUnitGetProperty(ca->outputUnit,
                            kAudioUnitProperty_StreamFormat,
                            kAudioUnitScope_Output,
                            0,
                            &outFormat,
                            &size)) {
        return -1;
    }

    if(AudioUnitSetProperty(ca->outputUnit, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Input, 0, &outFormat, size)) {
        return -1;
    }

    /* Specify the input PCM format */
    ca->channels = ao->channels;
    inFormat.mSampleRate = ao->rate;
    inFormat.mChannelsPerFrame = ao->channels;
    inFormat.mFormatID = kAudioFormatLinearPCM;
#ifdef _BIG_ENDIAN
    inFormat.mFormatFlags = kLinearPCMFormatFlagIsPacked | kLinearPCMFormatFlagIsBigEndian;
#else
    inFormat.mFormatFlags = kLinearPCMFormatFlagIsPacked;
#endif

    if (ao->signed_samples) {
        inFormat.mFormatFlags |= kLinearPCMFormatFlagIsSignedInteger;
    }

    ca->bps = ao->bytes_per_sample;

    inFormat.mBitsPerChannel = ca->bps << 3;
    inFormat.mBytesPerPacket = ca->bps*inFormat.mChannelsPerFrame;
    inFormat.mFramesPerPacket = 1;
    inFormat.mBytesPerFrame = ca->bps*inFormat.mChannelsPerFrame;

    /* Add our callback - but don't start it yet */
    memset(&renderCallback, 0, sizeof(AURenderCallbackStruct));
    renderCallback.inputProc = convertProc;
    renderCallback.inputProcRefCon = ao->userptr;
    if(AudioUnitSetProperty(ca->outputUnit,
                            kAudioUnitProperty_SetRenderCallback,
                            kAudioUnitScope_Input,
                            0,
                            &renderCallback,
                            sizeof(AURenderCallbackStruct))) {
        return -1;
    }


    /* Open an audio I/O stream and create converter */
    if (ao->rate > 0 && ao->channels >0 ) {
        int ringbuffer_len;

        if(AudioConverterNew(&inFormat, &outFormat, &(ca->converter))) {
            return -1;
        }
        if(ao->channels == 1) {
            SInt32 channelMap[2] = { 0, 0 };
            if(AudioConverterSetProperty(ca->converter, kAudioConverterChannelMap, sizeof(channelMap), channelMap)) {
                return -1;
            }
        }

        /* Initialise FIFO */
        ringbuffer_len = (ao->rate *
                          FIFO_DURATION *
                          ca->bps *
                          ao->channels);
        sfifo_init( &ca->fifo, ringbuffer_len );
    }

    return(0);
}

static void flush_coreaudio(audio_output_t *ao)
{
    mpg123_coreaudio_t* ca = (mpg123_coreaudio_t*)ao->userptr;

    /* Stop playback */
    if(AudioOutputUnitStop(ca->outputUnit)) {
        /* error("AudioOutputUnitStop failed"); */
    }
    ca->play=0;

    /* Empty out the ring buffer */
    sfifo_flush( &ca->fifo );
}

static int write_coreaudio(audio_output_t *ao, unsigned char *buf, int len)
{
    mpg123_coreaudio_t* ca = (mpg123_coreaudio_t*)ao->userptr;
    int written;

    /* If there is no room, then sleep for half the length of the FIFO */
    while (sfifo_space( &ca->fifo ) < len ) {
        usleep( (FIFO_DURATION/2) * 1000000 );
    }

    /* Store converted audio in ring buffer */
    written = sfifo_write( &ca->fifo, (char*)buf, len);
    if (written != len) {
        return -1;
    }

    /* Start playback now that we have something to play */
    if(!ca->play)
    {
        if(AudioOutputUnitStart(ca->outputUnit)) {
            return -1;
        }
        ca->play = 1;
    }

    return len;
}

static int close_coreaudio(audio_output_t *ao)
{
    mpg123_coreaudio_t* ca = (mpg123_coreaudio_t*)ao->userptr;

    if (ca) {
        ca->decode_done = 1;
        while(!ca->play_done && ca->play) usleep(10000);

        /* No matter the error code, we want to close it (by brute force if necessary) */
        AudioConverterDispose(ca->converter);
        AudioOutputUnitStop(ca->outputUnit);
        AudioUnitUninitialize(ca->outputUnit);
        CloseComponent(ca->outputUnit);

        /* Free the ring buffer */
        sfifo_close( &ca->fifo );

        /* Free the conversion buffer */
        if (ca->buffer) {
            free( ca->buffer );
            ca->buffer = NULL;
        }

    }

    return 0;
}

static int deinit_coreaudio(audio_output_t* ao)
{
    /* Free up memory */
    if (ao->userptr) {
        free( ao->userptr );
        ao->userptr = NULL;
    }

    /* Success */
    return 0;
}

static OSStatus convertProc(void *inRefCon,
                            AudioUnitRenderActionFlags *inActionFlags,
                            const AudioTimeStamp *inTimeStamp,
                            UInt32 inBusNumber,
                            UInt32 inNumFrames,
                            AudioBufferList *ioData)
{
    AudioStreamPacketDescription* outPacketDescription = NULL;
    mpg123_coreaudio_t* ca = (mpg123_coreaudio_t*)inRefCon;
    OSStatus err= noErr;

    err = AudioConverterFillComplexBuffer(ca->converter,
                                          playProc,
                                          inRefCon,
                                          &inNumFrames,
                                          ioData,
                                          outPacketDescription);

    return err;
}

static OSStatus playProc(AudioConverterRef inAudioConverter,
                         UInt32 *ioNumberDataPackets,
                         AudioBufferList *outOutputData,
                         AudioStreamPacketDescription
                         **outDataPacketDescription,
                         void* inClientData)
{
    mpg123_coreaudio_t *ca = (mpg123_coreaudio_t *)inClientData;
    long n;


    if(ca->last_buffer) {
        ca->play_done = 1;
        return noErr;
    }

    for(n = 0; n < outOutputData->mNumberBuffers; n++)
    {
        unsigned int wanted = *ioNumberDataPackets * ca->channels * ca->bps;
        unsigned char *dest;
        unsigned int read;
        if(ca->buffer_size < wanted) {
            ca->buffer = realloc( ca->buffer, wanted);
            ca->buffer_size = wanted;
        }
        dest = ca->buffer;

        /* Only play if we have data left */
        if ( sfifo_used( &ca->fifo ) < wanted ) {
            if(!ca->decode_done) {
                return -1;
            }
            wanted = sfifo_used( &ca->fifo );
            ca->last_buffer = 1;
        }

        /* Read audio from FIFO to SDL's buffer */
        read = sfifo_read( &ca->fifo, dest, wanted );

        outOutputData->mBuffers[n].mDataByteSize = read;
        outOutputData->mBuffers[n].mData = dest;
    }

    return noErr;
}

#include "sfifo.c"
