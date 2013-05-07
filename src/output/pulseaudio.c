#include "pulseaudio.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger
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

/*connects the context to the default PulseAudio server
  returns true on success, false on failure*/
static int connect_context(pa_context *context, pa_threaded_mainloop* mainloop);

static void context_state_callback(pa_context *context,
                                   pa_threaded_mainloop* mainloop);

/*connects the stream to the default PulseAudio output sink
  returns true on success, false on failure*/
static int connect_stream(pa_stream *stream, pa_threaded_mainloop* mainloop);

static void stream_state_callback(pa_stream *stream,
                                  pa_threaded_mainloop* mainloop);

struct get_volume_cb_data {
    pa_threaded_mainloop *mainloop;
    pa_cvolume *cvolume;
};

static void get_volume_callback(pa_context *context,
                                const pa_sink_info *info,
                                int eol,
                                struct get_volume_cb_data *cb_data);


static void set_volume_callback(pa_context *context,
                                int success,
                                pa_threaded_mainloop *mainloop);

static PyObject* PulseAudio_play(output_PulseAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* PulseAudio_pause(output_PulseAudio *self, PyObject *args)
{
    /*cork output stream*/
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* PulseAudio_resume(output_PulseAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* PulseAudio_flush(output_PulseAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* PulseAudio_get_volume(output_PulseAudio *self, PyObject *args)
{
    pa_cvolume cvolume;
    pa_operation *op;
    struct get_volume_cb_data cb_data = {self->mainloop, &cvolume};
    double max_volume;
    double norm_volume;

    pa_threaded_mainloop_lock(self->mainloop);

    /*query stream info for current sink*/
    op = pa_context_get_sink_info_by_index(
        self->context,
        pa_stream_get_device_index(self->stream),
        (pa_sink_info_cb_t)get_volume_callback,
        &cb_data);

    /*wait for callback to complete*/
    while (pa_operation_get_state(op) == PA_OPERATION_RUNNING) {
        pa_threaded_mainloop_wait(self->mainloop);
    }

    pa_operation_unref(op);

    pa_threaded_mainloop_unlock(self->mainloop);

    /*convert cvolume to double*/
    max_volume = pa_cvolume_max(&cvolume);
    norm_volume = PA_VOLUME_NORM;

    /*return double converted to Python object*/
    return PyFloat_FromDouble(max_volume / norm_volume);
}

static PyObject* PulseAudio_set_volume(output_PulseAudio *self, PyObject *args)
{
    pa_cvolume cvolume;
    pa_operation *op;
    struct get_volume_cb_data cb_data = {self->mainloop, &cvolume};
    double new_volume_d;
    pa_volume_t new_volume;

    if (!PyArg_ParseTuple(args, "d", &new_volume_d))
        return NULL;

    /*convert volume to integer pa_volume_t value between
      PA_VOLUME_MUTED and PA_VOLUME_NORM*/
    new_volume = round(new_volume_d * PA_VOLUME_NORM);

    pa_threaded_mainloop_lock(self->mainloop);

    /*query stream info for current sink*/
    op = pa_context_get_sink_info_by_index(
        self->context,
        pa_stream_get_device_index(self->stream),
        (pa_sink_info_cb_t)get_volume_callback,
        &cb_data);

    /*wait for callback to complete*/
    while (pa_operation_get_state(op) == PA_OPERATION_RUNNING) {
        pa_threaded_mainloop_wait(self->mainloop);
    }

    pa_operation_unref(op);

    /*scale values using the new volume setting*/
    pa_cvolume_scale(&cvolume, new_volume);

    /*set sink's volume values*/
    op = pa_context_set_sink_volume_by_index(
        self->context,
        pa_stream_get_device_index(self->stream),
        &cvolume,
        (pa_context_success_cb_t)set_volume_callback,
        self->mainloop);

    /*wait for callback to complete*/
    while (pa_operation_get_state(op) == PA_OPERATION_RUNNING) {
        pa_threaded_mainloop_wait(self->mainloop);
    }

    pa_operation_unref(op);

    pa_threaded_mainloop_unlock(self->mainloop);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* PulseAudio_close(output_PulseAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* PulseAudio_new(PyTypeObject *type,
                                PyObject *args,
                                PyObject *kwds)
{
    output_PulseAudio *self;

    self = (output_PulseAudio *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int PulseAudio_init(output_PulseAudio *self, PyObject *args, PyObject *kwds)
{
    int sample_rate;
    int channels;
    int bits_per_sample;
    char *stream_name;
    pa_sample_spec sample_spec;

    self->mainloop = NULL;
    self->mainloop_api = NULL;
    self->context = NULL;
    self->stream = NULL;

    if (!PyArg_ParseTuple(args, "iiis",
                          &sample_rate,
                          &channels,
                          &bits_per_sample,
                          &stream_name))
        return -1;

    /*sanity check output parameters*/
    if (sample_rate > 0) {
        sample_spec.rate = sample_rate;
    } else {
        PyErr_SetString(
            PyExc_ValueError, "sample rate must be a postive value");
        return -1;
    }

    if (channels > 0) {
        sample_spec.channels = channels;
    } else {
        PyErr_SetString(
            PyExc_ValueError, "channels must be a positive value");
        return -1;
    }

    /*use .wav-style sample format*/
    switch (bits_per_sample) {
    case 8:
        sample_spec.format = PA_SAMPLE_U8;
        break;
    case 16:
        sample_spec.format = PA_SAMPLE_S16LE;
        break;
    case 24:
        sample_spec.format = PA_SAMPLE_S24LE;
        break;
    default:
        PyErr_SetString(
            PyExc_ValueError, "bits-per-sample must be 8, 16 or 24");
        return -1;
    }

    /*setup PulseAudio mainloop and abstract mainloop API*/
    self->mainloop = pa_threaded_mainloop_new();
    if (pa_threaded_mainloop_start(self->mainloop)) {
        PyErr_SetString(
            PyExc_ValueError, "unable to start mainloop thread");
        return -1;
    }
    self->mainloop_api = pa_threaded_mainloop_get_api(self->mainloop);

    /*create new connection context*/
    if ((self->context = pa_context_new(self->mainloop_api,
                                        stream_name)) == NULL) {
        PyErr_SetString(
            PyExc_ValueError, "unable to create PulseAudio connection context");
        return -1;
    }

    if (!connect_context(self->context, self->mainloop)) {
        PyErr_SetString(
            PyExc_ValueError, "unable to connect to PulseAudio server");
        return -1;
    }

    /*create new connection stream*/
    if ((self->stream = pa_stream_new(self->context,
                                      stream_name,
                                      &sample_spec,
                                      NULL)) == NULL) {
        PyErr_SetString(
            PyExc_ValueError, "unable to create PulseAudio connection stream");
        return -1;
    }

    /*connect stream to context*/
    if (!connect_stream(self->stream, self->mainloop)) {
        PyErr_SetString(
            PyExc_ValueError, "unable to connect to PulseAudio output stream");
        return -1;
    }

    /*add stream write callback*/
    /*FIXME*/

    return 0;
}

void PulseAudio_dealloc(output_PulseAudio *self)
{
    /*disconnect stream*/
    if (self->stream != NULL) {
        pa_stream_disconnect(self->stream);
        pa_stream_unref(self->stream);
    }

    /*stop mainloop thread, if running*/
    if (self->mainloop != NULL)
        pa_threaded_mainloop_stop(self->mainloop);

    /*reduce the context's reference count*/
    if (self->context != NULL)
        pa_context_unref(self->context);

    /*deallocate PulseAudio main loop*/
    /*mainloop_api is owned by mainloop and need not be freed*/
    if (self->mainloop != NULL)
        pa_threaded_mainloop_free(self->mainloop);

    self->ob_type->tp_free((PyObject*)self);
}

static int connect_context(pa_context *context, pa_threaded_mainloop* mainloop)
{
    /*setup context change callback*/
    pa_context_set_state_callback(
        context,
        (pa_context_notify_cb_t)context_state_callback,
        mainloop);

    /*perform connection to PulseAudio server*/
    if (pa_context_connect(context, NULL, 0, NULL) >= 0) {
        pa_context_state_t state;

        /*wait for callback to indicate completion*/
        pa_threaded_mainloop_lock(mainloop);

        do {
            state = pa_context_get_state(context);

            if ((state == PA_CONTEXT_READY) ||
                (state == PA_CONTEXT_FAILED) ||
                (state == PA_CONTEXT_TERMINATED)) {
                break;
            } else {
                pa_threaded_mainloop_wait(mainloop);
            }
        } while (1);

        pa_threaded_mainloop_unlock(mainloop);

        /*remove context change callback now that it's no longer needed*/
        pa_context_set_state_callback(context, NULL, NULL);

        /*return whether connection is successful*/
        return state == PA_CONTEXT_READY;
    } else {
        pa_threaded_mainloop_unlock(mainloop);

        /*remove context change callback now that it's no longer needed*/
        pa_context_set_state_callback(context, NULL, NULL);

        return 0;
    }
}

static void context_state_callback(pa_context *context,
                                   pa_threaded_mainloop* mainloop)
{
    switch (pa_context_get_state(context)) {
    case PA_CONTEXT_UNCONNECTED:
    case PA_CONTEXT_CONNECTING:
    case PA_CONTEXT_AUTHORIZING:
    case PA_CONTEXT_SETTING_NAME:
        /*ignore work-in-progress states*/
        break;
    case PA_CONTEXT_READY:
    case PA_CONTEXT_FAILED:
    case PA_CONTEXT_TERMINATED:
        /*signal on success or failure states*/
        pa_threaded_mainloop_signal(mainloop, 0);
        break;
    }
}

static int connect_stream(pa_stream *stream, pa_threaded_mainloop* mainloop)
{
    /*setup stream state change callback*/
    pa_stream_set_state_callback(
        stream,
        (pa_stream_notify_cb_t)stream_state_callback,
        mainloop);

    /*perform connection to PulseAudio server's default output stream*/
    if (pa_stream_connect_playback(stream,
                                   NULL, /*device*/
                                   NULL, /*buffering attributes*/
                                   0,    /*flags*/
                                   NULL, /*volume*/
                                   NULL  /*sync stream*/) >= 0) {
        pa_stream_state_t state;

        /*wait for callback to indicate completion*/
        pa_threaded_mainloop_lock(mainloop);
        do {
            state = pa_stream_get_state(stream);

            if ((state == PA_STREAM_READY) ||
                (state == PA_STREAM_FAILED) ||
                (state == PA_STREAM_TERMINATED)) {
                break;
            } else {
                pa_threaded_mainloop_wait(mainloop);
            }
        } while (1);

        pa_threaded_mainloop_unlock(mainloop);

        /*remove stream change callback now that it's no longer needed*/
        pa_stream_set_state_callback(stream, NULL, NULL);

        /*return whether connection is successful*/
        return state == PA_STREAM_READY;
    } else {
        pa_threaded_mainloop_unlock(mainloop);

        /*remove stream change callback now that it's no longer needed*/
        pa_stream_set_state_callback(stream, NULL, NULL);

        return 0;
    }
}


static void stream_state_callback(pa_stream *stream,
                                  pa_threaded_mainloop* mainloop)
{
    switch (pa_stream_get_state(stream)) {
    case PA_STREAM_UNCONNECTED:
    case PA_STREAM_CREATING:
        /*ignore work-in-progress states*/
        break;
    case PA_STREAM_READY:
    case PA_STREAM_TERMINATED:
    case PA_STREAM_FAILED:
        /*signal on success or failure states*/
        pa_threaded_mainloop_signal(mainloop, 0);
        break;
    }
}

static void get_volume_callback(pa_context *context,
                                const pa_sink_info *info,
                                int eol,
                                struct get_volume_cb_data *cb_data)
{
    if (!eol) {
        *(cb_data->cvolume) = info->volume;
    }

    pa_threaded_mainloop_signal(cb_data->mainloop, 0);
}

static void set_volume_callback(pa_context *context,
                                int success,
                                pa_threaded_mainloop *mainloop)
{
    /*do nothing since there's no recourse if volume isn't set*/
    pa_threaded_mainloop_signal(mainloop, 0);
}
