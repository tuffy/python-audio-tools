#include <lame/lame.h>
#include "../pcmreader.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger

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

#define BLOCK_SIZE 4096
#define MP3BUF_SIZE 12320  /*1.25 * BLOCK_SIZE + 7200*/

PyObject*
encoders_encode_mp3(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    char *filename;
    FILE *output_file;
    struct PCMReader *pcmreader;
    static char *kwlist[] = {"filename",
                             "pcmreader",

                             "quality",
                             NULL};
    char *quality = NULL;
    lame_global_flags *gfp = NULL;
    int buffer[BLOCK_SIZE * 2];
    short int buffer_l[BLOCK_SIZE];
    short int buffer_r[BLOCK_SIZE];
    unsigned char mp3buf[MP3BUF_SIZE];
    unsigned pcm_frames;
    int to_output;

    if (!PyArg_ParseTupleAndKeywords(args, keywds, "sO&|s",
                                     kwlist,
                                     &filename,
                                     py_obj_to_pcmreader,
                                     &pcmreader,

                                     &quality)) {
        return NULL;
    }

    /*ensure PCMReader object is compatible with MP3 output*/
    if ((pcmreader->channels != 1) && (pcmreader->channels != 2)) {
        PyErr_SetString(PyExc_ValueError, "channel count must be 1 or 2");
        pcmreader->del(pcmreader);
        return NULL;
    }

    if (pcmreader->bits_per_sample != 16) {
        PyErr_SetString(PyExc_ValueError, "bits per sample must be 16");
        pcmreader->del(pcmreader);
        return NULL;
    }

    /*lame should resample anything not the proper sample rate*/

    /*open output file for writing*/
    if ((output_file = fopen(filename, "w+b")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        pcmreader->del(pcmreader);
        return NULL;
    }

    /*set error message callbacks*/
    /*FIXME*/

    /*initialize encoder*/
    if ((gfp = lame_init()) == NULL) {
        PyErr_SetString(PyExc_ValueError, "error initializing mp3lame");
        goto error;
    }

    /*set stream parameters from PCMReader*/
    if (pcmreader->channels == 2) {
        lame_set_num_channels(gfp, 2);
        lame_set_mode(gfp, 1); /*joint stereo*/
    } else {
        lame_set_num_channels(gfp, 1);
        lame_set_mode(gfp, 3); /*mono*/
    }

    lame_set_in_samplerate(gfp, pcmreader->sample_rate);

    /*set quality mode or preset from quality string, if set*/
    if (quality != NULL) {
        if (!strcmp(quality, "0")) {
            /*best quality, very slow*/
            lame_set_quality(gfp, 0);
        } else if (!strcmp(quality, "1")) {
            lame_set_quality(gfp, 1);
        } else if (!strcmp(quality, "2")) {
            /*near best quality, not too slow*/
            lame_set_quality(gfp, 2);
        } else if (!strcmp(quality, "3")) {
            lame_set_quality(gfp, 3);
        } else if (!strcmp(quality, "4")) {
            lame_set_quality(gfp, 4);
        } else if (!strcmp(quality, "5")) {
            /*good quality, fast*/
            lame_set_quality(gfp, 5);
        } else if (!strcmp(quality, "6")) {
            lame_set_quality(gfp, 6);
        } else if (!strcmp(quality, "7")) {
            /*ok quality, really fast*/
            lame_set_quality(gfp, 7);
        } else if (!strcmp(quality, "8")) {
            lame_set_quality(gfp, 8);
        } else if (!strcmp(quality, "9")) {
            /*worst quality*/
            lame_set_quality(gfp, 9);
        } else if (!strcmp(quality, "medium")) {
            lame_set_preset(gfp, MEDIUM);
        } else if (!strcmp(quality, "standard")) {
            lame_set_preset(gfp, STANDARD);
        } else if (!strcmp(quality, "extreme")) {
            lame_set_preset(gfp, EXTREME);
        } else if (!strcmp(quality, "insane")) {
            lame_set_preset(gfp, INSANE);
        }

        /*if none of these, use the default*/
    }

    /*set internal configuration*/
    if (lame_init_params(gfp) < 0) {
        PyErr_SetString(PyExc_ValueError,
                        "error initializing lame parameters");
        goto error;
    }

    /*for each non-empty FrameList from PCMReader, encode MP3 frame*/
    while ((pcm_frames = pcmreader->read(pcmreader, BLOCK_SIZE, buffer)) > 0) {
        unsigned i;
        if (pcmreader->channels == 2) {
            for (i = 0; i < pcm_frames; i++) {
                buffer_l[i] = (short int)buffer[i * 2];
                buffer_r[i] = (short int)buffer[i * 2 + 1];
            }
        } else {
            for (i = 0; i < pcm_frames; i++) {
                buffer_l[i] = buffer_r[i] = (short int)buffer[i];
            }
        }

        switch (to_output = lame_encode_buffer(gfp,
                                               buffer_l,
                                               buffer_r,
                                               pcm_frames,
                                               mp3buf,
                                               MP3BUF_SIZE)) {
        default:
            fwrite(mp3buf, sizeof(unsigned char), to_output, output_file);
            break;
        case -1:
            PyErr_SetString(PyExc_ValueError, "output buffer too small");
            goto error;
        case -2:
            PyErr_SetString(PyExc_ValueError, "error allocating data");
            goto error;
        case -3:
            PyErr_SetString(PyExc_ValueError, "lame_init_params() not called");
            goto error;
        case -4:
            PyErr_SetString(PyExc_ValueError, "psycho acoustic error");
            goto error;
        }
    }

    if (pcmreader->status != PCM_OK) {
        PyErr_SetString(PyExc_IOError, "I/O error from pcmreader");
        goto error;
    }

    /*flush remaining MP3 data*/
    to_output = lame_encode_flush(gfp, mp3buf, MP3BUF_SIZE);
    fwrite(mp3buf, sizeof(unsigned char), to_output, output_file);

    /*write Xing header to start of file*/
    lame_mp3_tags_fid(gfp, output_file);

    /*free internal LAME structures*/
    if (gfp != NULL)
        lame_close(gfp);

    fclose(output_file);
    pcmreader->del(pcmreader);
    Py_INCREF(Py_None);
    return Py_None;
error:
    /*free internal LAME structures*/
    if (gfp != NULL)
        lame_close(gfp);
    fclose(output_file);
    pcmreader->del(pcmreader);
    return NULL;
}
