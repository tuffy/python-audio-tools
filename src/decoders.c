#include <Python.h>
#include "decoders.h"
#ifdef HAS_MP3
#include <mpg123.h>
#endif

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

extern PyTypeObject decoders_FlacDecoderType;
extern PyTypeObject decoders_OggFlacDecoderType;
extern PyTypeObject decoders_SHNDecoderType;
extern PyTypeObject decoders_ALACDecoderType;
extern PyTypeObject decoders_WavPackDecoderType;
#ifdef HAS_VORBIS
extern PyTypeObject decoders_VorbisDecoderType;
#endif
#ifdef HAS_MP3
extern PyTypeObject decoders_MP3DecoderType;
#endif
#ifdef HAS_OPUS
extern PyTypeObject decoders_OpusDecoderType;
#endif
extern PyTypeObject decoders_TTADecoderType;
extern PyTypeObject decoders_DVDA_Title_Type;
extern PyTypeObject decoders_Sine_Mono_Type;
extern PyTypeObject decoders_Sine_Stereo_Type;
extern PyTypeObject decoders_Sine_Simple_Type;
extern PyTypeObject decoders_CPPMDecoderType;

PyMODINIT_FUNC
initdecoders(void)
{
    PyObject* m;

    decoders_FlacDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_FlacDecoderType) < 0)
        return;

    decoders_OggFlacDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_OggFlacDecoderType) < 0)
        return;

    decoders_SHNDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_SHNDecoderType) < 0)
        return;

    decoders_ALACDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_ALACDecoderType) < 0)
        return;

    decoders_WavPackDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_WavPackDecoderType) < 0)
        return;

    #ifdef HAS_VORBIS
    decoders_VorbisDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_VorbisDecoderType) < 0)
        return;
    #endif

    #ifdef HAS_MP3
    decoders_MP3DecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_MP3DecoderType) < 0)
        return;
    #endif

    #ifdef HAS_OPUS
    decoders_OpusDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_OpusDecoderType) < 0)
        return;
    #endif

    decoders_TTADecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_TTADecoderType) < 0)
        return;

    decoders_CPPMDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_CPPMDecoderType) < 0)
        return;

    decoders_DVDA_Title_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_DVDA_Title_Type) < 0)
        return;

    decoders_Sine_Mono_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_Sine_Mono_Type) < 0)
        return;

    decoders_Sine_Stereo_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_Sine_Stereo_Type) < 0)
        return;

    decoders_Sine_Simple_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_Sine_Simple_Type) < 0)
        return;

    m = Py_InitModule3("decoders", module_methods,
                       "Low-level audio format decoders");

    Py_INCREF(&decoders_FlacDecoderType);
    PyModule_AddObject(m, "FlacDecoder",
                       (PyObject *)&decoders_FlacDecoderType);

    Py_INCREF(&decoders_OggFlacDecoderType);
    PyModule_AddObject(m, "OggFlacDecoder",
                       (PyObject *)&decoders_OggFlacDecoderType);

    Py_INCREF(&decoders_SHNDecoderType);
    PyModule_AddObject(m, "SHNDecoder",
                       (PyObject *)&decoders_SHNDecoderType);

    Py_INCREF(&decoders_ALACDecoderType);
    PyModule_AddObject(m, "ALACDecoder",
                       (PyObject *)&decoders_ALACDecoderType);

    Py_INCREF(&decoders_WavPackDecoderType);
    PyModule_AddObject(m, "WavPackDecoder",
                       (PyObject *)&decoders_WavPackDecoderType);

    #ifdef HAS_VORBIS
    Py_INCREF(&decoders_VorbisDecoderType);
    PyModule_AddObject(m, "VorbisDecoder",
                       (PyObject *)&decoders_VorbisDecoderType);
    #endif

    #ifdef HAS_MP3
    Py_INCREF(&decoders_MP3DecoderType);
    PyModule_AddObject(m, "MP3Decoder",
                       (PyObject *)&decoders_MP3DecoderType);
    #endif

    #ifdef HAS_OPUS
    Py_INCREF(&decoders_OpusDecoderType);
    PyModule_AddObject(m, "OpusDecoder",
                       (PyObject *)&decoders_OpusDecoderType);
    #endif

    Py_INCREF(&decoders_TTADecoderType);
    PyModule_AddObject(m, "TTADecoder",
                       (PyObject *)&decoders_TTADecoderType);

    Py_INCREF(&decoders_CPPMDecoderType);
    PyModule_AddObject(m, "CPPMDecoder",
                       (PyObject *)&decoders_CPPMDecoderType);

    Py_INCREF(&decoders_DVDA_Title_Type);
    PyModule_AddObject(m, "DVDA_Title",
                       (PyObject *)&decoders_DVDA_Title_Type);

    Py_INCREF(&decoders_Sine_Mono_Type);
    PyModule_AddObject(m, "Sine_Mono",
                       (PyObject *)&decoders_Sine_Mono_Type);

    Py_INCREF(&decoders_Sine_Stereo_Type);
    PyModule_AddObject(m, "Sine_Stereo",
                       (PyObject *)&decoders_Sine_Stereo_Type);

    Py_INCREF(&decoders_Sine_Simple_Type);
    PyModule_AddObject(m, "Sine_Simple",
                       (PyObject *)&decoders_Sine_Simple_Type);

    #ifdef HAS_MP3
    /*this initializes the library's static decoding tables

      although the library has an mpg123_exit() function
      to be called at shutdown-time, it's currenly a noop
      so we won't worry about it*/
    mpg123_init();
    #endif
}
