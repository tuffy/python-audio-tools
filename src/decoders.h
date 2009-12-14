#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2009  Brian Langenberger

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

#include "bitstream.h"
#include "array.h"

PyObject *decoders_read_bits(PyObject *dummy, PyObject *args);
PyObject *decoders_read_unary(PyObject *dummy, PyObject *args);

PyMethodDef module_methods[] = {
  {"read_bits",(PyCFunction)decoders_read_bits,
   METH_VARARGS,""},
  {"read_unary",(PyCFunction)decoders_read_unary,
   METH_VARARGS,""},
  {NULL}
};

#include "decoders/flac.h"


const static unsigned int read_bits_table[0x900][8] =
#include "read_bits_table.h"
  ;

const static unsigned int read_unary_table[0x900][2] =
#include "read_unary_table.h"
  ;

static inline unsigned int read_bits(Bitstream* bs, unsigned int count) {
  int context = bs->state;
  unsigned int result;
  unsigned int byte;
  struct bs_callback* callback;
  unsigned int accumulator = 0;

  while (count > 0) {
    if (context == 0) {
      byte = (unsigned int)fgetc(bs->file);
      context = 0x800 | byte;
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
    }

    result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

    accumulator = (accumulator << ((result & 0xF00000) >> 20)) |
      ((result & 0xFF000) >> 12);
    count -= ((result & 0xF00000) >> 20);
    context = (result & 0xFFF);
  }

  bs->state = context;
  return accumulator;
}

static inline int read_signed_bits(Bitstream* bs, unsigned int count) {
  if (!read_bits(bs,1)) {
    return read_bits(bs,count - 1);
  } else {
    return read_bits(bs,count - 1) - (1 << (count - 1));
  }
}

static inline uint64_t read_bits64(Bitstream* bs, unsigned int count) {
  int context = bs->state;
  unsigned int result;
  unsigned int byte;
  struct bs_callback* callback;
  uint64_t accumulator = 0;

  while (count > 0) {
    if (context == 0) {
      byte = (unsigned int)fgetc(bs->file);
      context = 0x800 | byte;
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
    }

    result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

    accumulator = (accumulator << ((result & 0xF00000) >> 20)) |
      ((result & 0xFF000) >> 12);
    count -= ((result & 0xF00000) >> 20);
    context = (result & 0xFFF);
  }

  bs->state = context;
  return accumulator;
}

static inline unsigned int read_unary(Bitstream* bs, int stop_bit) {
  int context = bs->state;
  unsigned int result;
  struct bs_callback* callback;
  unsigned int byte;
  unsigned int accumulator = 0;

  do {
    if (context == 0) {
      byte = (unsigned int)fgetc(bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
      context = 0x800 | byte;
    }

    result = read_unary_table[context][stop_bit];

    accumulator += ((result & 0xFF000) >> 12);

    context = result & 0xFFF;
  } while (result >> 24);

  bs->state = context;
  return accumulator;
}

static inline void byte_align_r(Bitstream* bs) {
  bs->state = 0;
}
