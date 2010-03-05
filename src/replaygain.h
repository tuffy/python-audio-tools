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
#endif
