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

enum {HUFFMAN_MISSING_LEAF = -1};

/*given a set of huffman_frequency values
  (followed by a 0 length terminator frequency)
  and BS_BIG_ENDIAN or BS_LITTLE_ENDIAN,
  compiles the Huffman tree into a jump table
  suitable for use by bitstream->read_huffman_code

  the jump table must be freed when no longer needed

  returns the number of rows in the table,
  or a negative value if there's an error
  whose value is taken from the preceding enum
*/
int compile_huffman_table(struct bs_huffman_table (**table)[][0x200],
                          struct huffman_frequency* frequencies,
                          bs_endianness endianness);


/*The bitstream reader operates on jump tables that have been
  compiled from the original Huffman tree.

  Using this module as a standalone binary,
  one can compile JSON source into jump tables suitable
  for importing into C code.  Such as with:

  % huffman -i table.json > table.h

  where "table.h" is imported in source code with:

  struct bs_huffman_table table[][0x200] =
  #include "table.h"
  ;

  and called from the bitstream reader with:

  value = bitstream->read_huffman_code(bitstream, table);

  This is the preferred method of handling static Huffman trees
  which are the same for every file in a particular format.


  However, for Huffman trees which are defined at runtime,
  one will need to compile the jump table directly.
  For example, given a set of frequency values:

  struct huffman_frequency frequencies[] = {
      {1, 1, 0}, // bits = 1      value = 0
      {1, 2, 1}, // bits = 0 1    value = 1
      {1, 3, 2}, // bits = 0 0 1  value = 2
      {0, 3, 3}, // bits = 0 0 0  value = 3
      {0, 0, 0}  // terminator
     };

  we compile them to a table with:

  struct bs_huffman_table (*table)[][0x200];
  compile_huffman_table(&table, frequencies, BS_BIG_ENDIAN);

  and call that table from the bitstream reader with:

  value = bitstream->read_huffman_code(bitstream, *table);

  before finally deallocating the table with:

  free(table);

  For real code, the "frequencies" array will be allocated at runtime
  but can be deallocated immediately once "table" has been compiled.
  In addition, real code will want to check the return value of
  "compile_huffman_table" in case of an incorrectly specified Huffman tree.
*/

#endif
