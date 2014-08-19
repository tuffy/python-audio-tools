#include "bitstream.h"
#ifndef HUFFMAN_H
#define HUFFMAN_H

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

struct huffman_frequency {
    unsigned int bits;   /*the bits to be consumed
                           from most-significant to least-significant
                           in the tree*/

    unsigned int length; /*the total length of bits leading to the leaf node*/

    int value;           /*the final value in the leaf node*/
};

enum {
    /*triggered by an incomplete Huffman table, such as:
      [[1], 0,
       [0, 1], 1]]
      where the value for [0, 0] isn't specified*/
    HUFFMAN_MISSING_LEAF = -1,

    /*triggered by an overfilled Huffman table, such as:
      [[1], 0,
       [0, 1], 1,
       [0, 0], 2,
       [0, 0], 3]
      where the value for [0, 0] is specified multiple times*/
    HUFFMAN_DUPLICATE_LEAF = -2,

    /*triggered by a Huffman table where leaves are unreachable, such as:
      [[1], 0,
       [0], 1,
       [0, 0], 2,
       [0, 1], 3]
      where the values [0, 0] and [0, 1] are unreachable since [0] is a leaf*/
    HUFFMAN_ORPHANED_LEAF = -3,

    HUFFMAN_EMPTY_TREE = -4
};

/*given a set of huffman_frequency values,
  the total number of frequency values
  and BS_BIG_ENDIAN or BS_LITTLE_ENDIAN,
  compiles the Huffman tree into a jump table
  suitable for use by bitstream->read_huffman_code

  the jump table must be freed when no longer needed

  returns the number of rows in the table,
  or a negative value if there's an error
  (whose value is taken from the preceding enum)
*/
int compile_br_huffman_table(br_huffman_table_t** table,
                             struct huffman_frequency* frequencies,
                             unsigned int total_frequencies,
                             bs_endianness endianness);


/*The bitstream reader operates on jump tables that have been
  compiled from the original Huffman tree.

  Using this module as a standalone binary,
  one can compile JSON source into jump tables suitable
  for importing into C code.  For example, given the JSON file:

  [[1], 0,
   [0, 1], 1,
   [0, 0, 1], 2,
   [0, 0, 0], 3]

  We compile it to a jump table with:

  % huffman -i table.json > table.h

  where "table.h" is imported in source code with:

  struct br_huffman_table table[][0x200] =
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
      {1, 1, 0},  // bits = 1      value = 0
      {1, 2, 1},  // bits = 0 1    value = 1
      {1, 3, 2},  // bits = 0 0 1  value = 2
      {0, 3, 3}}  // bits = 0 0 0  value = 3
     };

  we compile them to a table with:

  struct br_huffman_table (*table)[][0x200];
  compile_br_huffman_table(&table, frequencies, 4, BS_BIG_ENDIAN);

  and call that table from the bitstream reader with:

  value = bitstream->read_huffman_code(bitstream, *table);

  before finally deallocating the table with:

  free(table);

  For real code, the "frequencies" array will be allocated at runtime
  but can be deallocated immediately once "table" has been compiled.
  In addition, real code will want to check the return value of
  "compile_br_huffman_table" in case of an incorrectly specified Huffman tree.
*/


/*given a set of huffman_frequency values,
  the total number of frequency values
  and BS_BIG_ENDIAN or BS_LITTLE_ENDIAN,
  compiles the Huffman tree into a binary tree
  suitable for use by bitstream->write_huffman_code

  the tree must be freed with free_bw_huffman_table when no longer needed

  returns 0 on success,
  or a negative value if there's an error
*/
int compile_bw_huffman_table(struct bw_huffman_table** table,
                             struct huffman_frequency* frequencies,
                             unsigned int total_frequencies,
                             bs_endianness endianness);

void free_bw_huffman_table(struct bw_huffman_table* table);

#endif
