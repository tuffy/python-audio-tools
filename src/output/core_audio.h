#include <Python.h>
#include <CoreServices/CoreServices.h>
#include <AudioUnit/AudioUnit.h>
#include <AudioToolbox/AudioToolbox.h>
#include "sfifo.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger and the mpg123 project
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


/* Duration of the ring buffer in seconds */
#define FIFO_DURATION       (1.0f)

typedef struct audio_output_struct
{
    int fn;         /* filenumber */
    void *userptr;  /* driver specific pointer */

    /* Callbacks */
    int (*open)(struct audio_output_struct *);
    int (*write)(struct audio_output_struct *, unsigned char *,int);
    void (*pause)(struct audio_output_struct *);
    void (*resume)(struct audio_output_struct *);
    void (*flush)(struct audio_output_struct *);
    int (*close)(struct audio_output_struct *);
    int (*deinit)(struct audio_output_struct *);

    long rate;      /* sample rate */
    int channels;   /* number of channels */
    int bytes_per_sample;
    int signed_samples;
} audio_output_t;

typedef struct mpg123_coreaudio
{
    AudioDeviceID output_device;
    AudioConverterRef converter;
    AudioUnit outputUnit;
    int open;
    char play;
    int channels;
    int bps;
    int last_buffer;
    int play_done;
    int decode_done;

    /* Convertion buffer */
    unsigned char * buffer;
    size_t buffer_size;

    /* Ring buffer */
    sfifo_t fifo;
} mpg123_coreaudio_t;


typedef struct {
    PyObject_HEAD

    audio_output_t* ao;
    int closed;
} output_CoreAudio;

static PyObject* CoreAudio_play(output_CoreAudio *self, PyObject *args);
static PyObject* CoreAudio_pause(output_CoreAudio *self, PyObject *args);
static PyObject* CoreAudio_resume(output_CoreAudio *self, PyObject *args);
static PyObject* CoreAudio_flush(output_CoreAudio *self, PyObject *args);
static PyObject* CoreAudio_get_volume(output_CoreAudio *self, PyObject *args);
static PyObject* CoreAudio_set_volume(output_CoreAudio *self, PyObject *args);
static PyObject* CoreAudio_close(output_CoreAudio *self, PyObject *args);

static PyObject* CoreAudio_new(PyTypeObject *type,
                               PyObject *args,
                               PyObject *kwds);
void CoreAudio_dealloc(output_CoreAudio *self);
int CoreAudio_init(output_CoreAudio *self, PyObject *args, PyObject *kwds);

PyGetSetDef CoreAudio_getseters[] = {
    {NULL}
};

PyMethodDef CoreAudio_methods[] = {
    {"play", (PyCFunction)CoreAudio_play, METH_VARARGS, ""},
    {"pause", (PyCFunction)CoreAudio_pause, METH_NOARGS, ""},
    {"resume", (PyCFunction)CoreAudio_resume, METH_NOARGS, ""},
    {"flush", (PyCFunction)CoreAudio_flush, METH_NOARGS, ""},
    {"get_volume", (PyCFunction)CoreAudio_get_volume, METH_NOARGS, ""},
    {"set_volume", (PyCFunction)CoreAudio_set_volume, METH_VARARGS, ""},
    {"close", (PyCFunction)CoreAudio_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject output_CoreAudioType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "output.CoreAudio",        /*tp_name*/
    sizeof(output_CoreAudio),  /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)CoreAudio_dealloc, /*tp_dealloc*/
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
    "CoreAudio objects",       /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    CoreAudio_methods,         /* tp_methods */
    0,                         /* tp_members */
    CoreAudio_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CoreAudio_init,  /* tp_init */
    0,                         /* tp_alloc */
    CoreAudio_new,             /* tp_new */
};

static int init_coreaudio(audio_output_t* ao,
                          long sample_rate,
                          int channels,
                          int bytes_per_sample,
                          int signed_samples);
static int open_coreaudio(audio_output_t *ao);
static void flush_coreaudio(audio_output_t *ao);
static int write_coreaudio(audio_output_t *ao, unsigned char *buf, int len);
static void pause_coreaudio(audio_output_t *ao);
static void resume_coreaudio(audio_output_t *ao);
static int close_coreaudio(audio_output_t *ao);
static int deinit_coreaudio(audio_output_t* ao);

static OSStatus convertProc(void *inRefCon,
                            AudioUnitRenderActionFlags *inActionFlags,
                            const AudioTimeStamp *inTimeStamp,
                            UInt32 inBusNumber,
                            UInt32 inNumFrames,
                            AudioBufferList *ioData);

static OSStatus playProc(AudioConverterRef inAudioConverter,
                         UInt32 *ioNumberDataPackets,
                         AudioBufferList *outOutputData,
                         AudioStreamPacketDescription
                         **outDataPacketDescription,
                         void* inClientData);

static OSStatus get_volume_scalar(AudioDeviceID output_device,
                                  UInt32 channel,
                                  Float32 *volume);
static OSStatus set_volume_scalar(AudioDeviceID output_device,
                                  UInt32 channel,
                                  Float32 volume);
