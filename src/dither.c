/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

/*this is quite similar to br_read_python
  except that it pulls data from os.urandom()*/
static unsigned
read_os_random(PyObject* os_module,
               uint8_t* buffer,
               unsigned buffer_size)
{
    /*call unrandom() function on os module*/
    PyObject* read_result =
        PyObject_CallMethod(os_module, "urandom", "I", buffer_size);
    char *string;
    Py_ssize_t string_size;
    unsigned to_copy;

    if (read_result == NULL) {
        /*some exception occurred, so clear result and return no bytes
          (which will likely turn into an I/O exception later)*/
        PyErr_Clear();
        return 0;
    }

    /*get string data from returned object*/
    if (PyBytes_AsStringAndSize(read_result,
                                &string,
                                &string_size) == -1) {
        /*got something that wasn't a string from .read()
          so clear exception and return no bytes*/
        Py_DECREF(read_result);
        PyErr_Clear();
        return 0;
    }

    /*write either "buffer_size" or "string_size" bytes to buffer
      whichever is less*/
    if (string_size >= buffer_size) {
        /*truncate strings larger than expected*/
        to_copy = buffer_size;
    } else {
        to_copy = (unsigned)string_size;
    }

    memcpy(buffer, (uint8_t*)string, to_copy);

    /*perform cleanup and return bytes actually read*/
    Py_DECREF(read_result);

    return to_copy;
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
                                NULL, /*unseekable stream*/
                                (ext_close_f)close_os_random,
                                (ext_free_f)free_os_random);
    } else {
        return NULL;
    }
}
