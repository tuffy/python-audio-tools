#include "bitstream_r.h"
#ifndef HUFFMAN_H
#define HUFFMAN_H

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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

struct huffman_frequency {
    unsigned int bits;
    unsigned int length;
    int value;
};

/*given a set of huffman_frequency values
  (followed by a 0 length terminator frequency)
  and BS_BIG_ENDIAN or BS_LITTLE_ENDIAN,
  compiles the Huffman tree into a jump table
  suitable for use by bitstream->read_huffman_code

  the jump table must be freed when no longer needed

  returns the number of rows in the table,
  or a negative value if there's an error
*/
int compile_huffman_table(struct bs_huffman_table (**table)[][0x200],
                          struct huffman_frequency* frequencies,
                          bs_endianness endianness);

#endif
