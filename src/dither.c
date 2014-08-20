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

/*This is a set of reusable routines for opening a BitstreamReader
  wrapped around the os.urandom function call
  for generating individual bits of dither for an audio stream.*/

static int
read_os_random(PyObject* os_module,
               struct bs_buffer* buffer,
               unsigned buffer_size)
{
    PyObject* string;

    /*call os.urandom() and retrieve a Python object*/
    if ((string = PyObject_CallMethod(os_module,
                                      "urandom", "I", buffer_size)) != NULL) {
        char *buffer_s;
        Py_ssize_t buffer_len;

        /*convert Python object to string and length*/
        if (PyString_AsStringAndSize(string, &buffer_s, &buffer_len) != -1) {
            /*extend buffer for additional data*/
            buf_write(buffer, (uint8_t*)buffer_s, (unsigned)buffer_len);

            /*DECREF Python object and return OK*/
            Py_DECREF(string);
            return 0;
        } else {
            /*os.urandom() didn't return a string
              so print error and clear it*/
            Py_DECREF(string);
            PyErr_Print();
            return 1;
        }
    } else {
        /*error occured in os.urandom() call
          so print error and clear it*/
        PyErr_Print();
        return 1;
    }
}

static void
close_os_random(PyObject* os_module)
{
    return;  /* does nothing*/
}

static void
free_os_random(PyObject* os_module)
{
    Py_XDECREF(os_module);
}

/*returns a BitstreamReader for reading 1 bit white noise dither values
  or NULL if an error occurs opening the os module*/
static BitstreamReader*
open_dither(void)
{
    PyObject* os_module;

    if ((os_module = PyImport_ImportModule("os")) != NULL) {
        return br_open_external(os_module,
                                BS_BIG_ENDIAN,
                                4096,
                                (ext_read_f)read_os_random,
                                NULL, /*unseekable stream*/
                                NULL, /*unseekable stream*/
                                NULL, /*unseekable stream*/
                                (ext_close_f)close_os_random,
                                (ext_free_f)free_os_random);
    } else {
        return NULL;
    }
}
