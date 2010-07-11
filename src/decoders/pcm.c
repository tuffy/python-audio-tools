static PyObject*
ia_array_to_framelist(struct ia_array *data,
                      int bits_per_sample) {
    return ia_array_slice_to_framelist(data,
                                       bits_per_sample,
                                       0,
                                       data->arrays[0].size);
}

static PyObject*
ia_array_slice_to_framelist(struct ia_array *data,
                            int bits_per_sample,
                            int start_frame,
                            int end_frame) {
    PyObject *pcm = NULL;
    pcm_FrameList *framelist;
    struct i_array channel_data;
    int32_t i, j;
    int channel;

    if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return NULL;
    framelist = (pcm_FrameList*)PyObject_CallMethod(pcm, "__blank__", NULL);
    Py_DECREF(pcm);
    if (framelist == NULL)
        return NULL;

    framelist->frames = end_frame - start_frame;
    framelist->channels = data->size;
    framelist->bits_per_sample = bits_per_sample;
    framelist->samples_length = framelist->frames * framelist->channels;
    framelist->samples = realloc(framelist->samples,
                                 sizeof(ia_data_t) *
                                 framelist->samples_length);

    for (channel = 0; channel < data->size; channel++) {
        channel_data = data->arrays[channel];
        for (i = channel, j = start_frame;
             j < end_frame;
             i += data->size, j++)
            framelist->samples[i] = channel_data.data[j];
    }

    return (PyObject*)framelist;
}

