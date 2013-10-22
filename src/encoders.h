#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

PyObject*
encoders_encode_flac(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_shn(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_alac(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_wavpack(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_tta(PyObject *dummy, PyObject *args, PyObject *keywds);

#ifdef HAS_MP3
PyObject*
encoders_encode_mp3(PyObject *dummy, PyObject *args, PyObject *keywds);
#endif

#ifdef HAS_MP2
PyObject*
encoders_encode_mp2(PyObject *dummy, PyObject *args, PyObject *keywds);
#endif

#ifdef HAS_VORBIS
PyObject*
encoders_encode_vorbis(PyObject *dummy, PyObject *args, PyObject *keywds);
#endif

PyMethodDef module_methods[] = {
    {"encode_flac", (PyCFunction)encoders_encode_flac,
     METH_VARARGS | METH_KEYWORDS, "Encode FLAC file from PCMReader"},
    {"encode_shn", (PyCFunction)encoders_encode_shn,
     METH_VARARGS | METH_KEYWORDS, "Encode Shorten file from PCMReader"},
    {"encode_alac", (PyCFunction)encoders_encode_alac,
     METH_VARARGS | METH_KEYWORDS, "Encode ALAC file from PCMReader"},
    {"encode_wavpack", (PyCFunction)encoders_encode_wavpack,
     METH_VARARGS | METH_KEYWORDS, "Encode WavPack file from PCMReader"},
    {"encode_tta", (PyCFunction)encoders_encode_tta,
     METH_VARARGS | METH_KEYWORDS, "Encode TTA file from PCMReader"},
    #ifdef HAS_MP3
    {"encode_mp3", (PyCFunction)encoders_encode_mp3,
     METH_VARARGS | METH_KEYWORDS, "Encode MP3 file from PCMReader"},
    #endif
    #ifdef HAS_MP2
    {"encode_mp2", (PyCFunction)encoders_encode_mp2,
    METH_VARARGS | METH_KEYWORDS, "Encode MP2 file from PCMReader"},
    #endif
    #ifdef HAS_VORBIS
    {"encode_vorbis", (PyCFunction)encoders_encode_vorbis,
    METH_VARARGS | METH_KEYWORDS, "Encode Vorbis file from PCMReader"},
    #endif
    {NULL}
};
