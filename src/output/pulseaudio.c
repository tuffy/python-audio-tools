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

static void context_state_callback(pa_context *context, void *userdata);

static pa_cvolume get_current_volume(pa_mainloop* mainloop,
                                     pa_context *context,
                                     uint32_t sink_index);

static void get_volume_callback(pa_context *context,
                                const pa_sink_info *i,
                                int eol,
                                void *userdata);

static void set_volume_callback(pa_context *context,
                                int success,
                                void *userdata);

static PyObject* PulseAudio_play(output_PulseAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* PulseAudio_pause(output_PulseAudio *self, PyObject *args)
{
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
    if (self->status == PA_CONNECTED) {
        pa_cvolume cvolume = get_current_volume(self->mainloop,
                                                self->context,
                                                self->master_sink_index);
        const double max_volume = pa_cvolume_max(&cvolume);
        const double norm_volume = PA_VOLUME_NORM;

        return PyFloat_FromDouble(max_volume / norm_volume);
    } else {
        return PyFloat_FromDouble(0.0);
    }
}

static PyObject* PulseAudio_set_volume(output_PulseAudio *self, PyObject *args)
{
    double new_volume_d;
    pa_volume_t new_volume;
    pa_cvolume current_volume;
    pa_operation *op;

    if (!PyArg_ParseTuple(args, "d", &new_volume_d))
        return NULL;

    /*convert volume to integer pa_volume_t value between
      PA_VOLUME_MUTED and PA_VOLUME_NORM*/
    new_volume = round(new_volume_d * PA_VOLUME_NORM);

    /*get sink's current volume as a pa_cvolume set of values*/
    current_volume = get_current_volume(self->mainloop,
                                        self->context,
                                        self->master_sink_index);

    /*scale values using the new volume setting*/
    pa_cvolume_scale(&current_volume, new_volume);

    /*set sink's volume values*/
    op = pa_context_set_sink_volume_by_index(
        self->context,
        self->master_sink_index,
        &current_volume,
        set_volume_callback,
        NULL);

    /*wait for callback to complete successfully*/
    while (pa_operation_get_state(op) == PA_OPERATION_RUNNING) {
        pa_mainloop_iterate(self->mainloop, 1, NULL);
    }

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
    char *stream_name;

    self->mainloop = NULL;
    self->mainloop_api = NULL;
    self->context = NULL;
    self->status = PA_CONNECTING;
    /*FIXME - discover master sink at runtime*/
    self->master_sink_index = 0;

    if (!PyArg_ParseTuple(args, "s", &stream_name))
        return -1;

    /*setup PulseAudio mainloop and abstract mainloop API*/
    self->mainloop = pa_mainloop_new();
    self->mainloop_api = pa_mainloop_get_api(self->mainloop);

    /*create new connection context*/
    if ((self->context = pa_context_new(self->mainloop_api,
                                        stream_name)) == NULL) {
        PyErr_SetString(
            PyExc_ValueError, "unable to create PulseAudio connection context");
        return -1;
    }

    /*connect context to server*/
    pa_context_connect(self->context, NULL, 0, NULL);

    /*add state callback which will perform initialization*/
    pa_context_set_state_callback(self->context, context_state_callback, self);

    /*iterate over the mainloop until a connection is established (or not)*/
    do {
        pa_mainloop_iterate(self->mainloop, 1, NULL);
    } while (self->status == PA_CONNECTING);

    if (self->status == PA_CONNECTED) {
        return 0;
    } else {
        PyErr_SetString(
            PyExc_ValueError, "unable to connect to PulseAudio server");
        return -1;
    }
}

void PulseAudio_dealloc(output_PulseAudio *self)
{
    /*stop mainloop thread, if running*/
    if (self->mainloop != NULL)
        pa_mainloop_quit(self->mainloop, 1);

    /*reduce the context's reference count*/
    if (self->context != NULL)
        pa_context_unref(self->context);

    /*deallocate PulseAudio main loop*/
    /*mainloop_api is owned by mainloop and need not be freed*/
    if (self->mainloop != NULL)
        pa_mainloop_free(self->mainloop);

    self->ob_type->tp_free((PyObject*)self);
}

static void context_state_callback(pa_context *context, void *userdata)
{
    output_PulseAudio *self = userdata;
    switch (pa_context_get_state(context)) {
    case PA_CONTEXT_UNCONNECTED:
    case PA_CONTEXT_CONNECTING:
    case PA_CONTEXT_AUTHORIZING:
    case PA_CONTEXT_SETTING_NAME:
        /*indicate stream is still connecting*/
        self->status = PA_CONNECTING;
        return;
    case PA_CONTEXT_READY:
        /*indicate stream is up and ready to go*/
        self->status = PA_CONNECTED;
        return;
    case PA_CONTEXT_FAILED:
    case PA_CONTEXT_TERMINATED:
    default:
        /*indicate connection is finished*/
        self->status = PA_FINISHED;
        return;
    }
}

static pa_cvolume get_current_volume(pa_mainloop* mainloop,
                                     pa_context *context,
                                     uint32_t sink_index)
{
    pa_cvolume volume;
    pa_operation *op = pa_context_get_sink_info_by_index(
        context,
        sink_index,
        get_volume_callback,
        &volume);

    while (pa_operation_get_state(op) == PA_OPERATION_RUNNING) {
        pa_mainloop_iterate(mainloop, 1, NULL);
    }

    return volume;
}

static void get_volume_callback(pa_context *context,
                                const pa_sink_info *info,
                                int eol,
                                void *userdata)
{
    if (!eol) {
        pa_cvolume *cvolume = userdata;
        *cvolume = info->volume;
    }
}

static void set_volume_callback(pa_context *context,
                                int success,
                                void *userdata)
{
    /*do nothing*/
    return;
}
