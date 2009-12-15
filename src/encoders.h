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

/*given an pcmreader object,
  extracts callable "read", and "close" methods
  and "sample_rate", "channels" and "bits_per_sample" int attributes
  returns 1 on success, 0 on failure (with exception set)*/
int parse_pcmreader(PyObject *pcmreader,
		    PyObject **read,
		    PyObject **close,
		    long *sample_rate,
		    long *channels,
		    long *bits_per_sample);

PyObject *encoders_write_bits(PyObject *dummy, PyObject *args);
PyObject *encoders_write_unary(PyObject *dummy, PyObject *args);

#include "encoders/flac.h"

PyMethodDef module_methods[] = {
  {"write_bits",(PyCFunction)encoders_write_bits,
   METH_VARARGS,""},
  {"write_unary",(PyCFunction)encoders_write_unary,
   METH_VARARGS,""},
  {"encode_flac",(PyCFunction)encoders_encode_flac,
   METH_VARARGS,""},
  {NULL}
};

const static unsigned int write_bits_table[0x400][0x900] =
#include "write_bits_table.h"
  ;

const static unsigned int write_unary_table[0x400][0x20] =
#include "write_unary_table.h"
    ;

static inline void write_bits(Bitstream* bs, unsigned int count, int value) {
  int bits_to_write;
  int value_to_write;
  int result;
  int context = bs->state;
  unsigned int byte;
  struct bs_callback* callback;

  while (count > 0) {
    /*chop off up to 8 bits to write at a time*/
    bits_to_write = count > 8 ? 8 : count;
    value_to_write = value >> (count - bits_to_write);

    /*feed them through the jump table*/
    result = write_bits_table[context][(value_to_write | (bits_to_write << 8))];

    /*write a byte if necessary*/
    if (result >> 18) {
      byte = (result >> 10) & 0xFF;
      fputc(byte,bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
    }

    /*update the context*/
    context = result & 0x3FF;

    /*decrement the count and value*/
    value -= (value_to_write << (count - bits_to_write));
    count -= bits_to_write;
  }
  bs->state = context;
}

static inline void write_unary(Bitstream* bs, int stop_bit, int value) {
  int result;
  int context = bs->state;
  unsigned int byte;
  struct bs_callback* callback;

  /*send continuation blocks until we get to 7 bits or less*/
  while (value >= 8) {
    result = write_unary_table[context][(stop_bit << 4) | 0x08];
    if (result >> 18) {
      byte = (result >> 10) & 0xFF;
      fputc(byte,bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
    }

    context = result & 0x3FF;

    value -= 8;
  }

  /*finally, send the remaning value*/
  result = write_unary_table[context][(stop_bit << 4) | value];

  if (result >> 18) {
    byte = (result >> 10) & 0xFF;
    fputc(byte,bs->file);
    for (callback = bs->callback; callback != NULL; callback = callback->next)
      callback->callback(byte,callback->data);
  }

  context = result & 0x3FF;
  bs->state = context;
}

static inline void byte_align_w(Bitstream* bs) {
  write_bits(bs,7,0);
  bs->state = 0;
}
