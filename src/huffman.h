#include "bitstream_r.h"


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
    void* value;
};

typedef enum {NODE_TREE, NODE_LEAF} huffman_node_type;

struct huffman_node {
    huffman_node_type type;
    union {
        void* leaf;
        struct {
            struct huffman_node* bit_0;
            struct huffman_node* bit_1;
        } tree;
    } v;
};

/*Takes a list Huffman frequencies, sorted by increasing length
  and returns a completed Huffman tree.
  The final huffman_frequency in the list should have a length of 0
  and serve as our list terminator.
  The tree must be freed when no longer needed.*/
struct huffman_node* build_huffman_tree(struct huffman_frequency* frequencies);

/*The proper recursive version, probably not to be called directly.*/
struct huffman_node* build_huffman_tree_(unsigned int bits,
                                         unsigned int length,
                                         struct huffman_frequency* frequencies
                                         );

/*Deallocates the space for the Huffman tree*/
void free_huffman_tree(struct huffman_node* node);

/*Given a Huffman tree and bitstream,
  traverses the tree bit-by-bit and returns the appropriate value.*/
void* get_huffman_value(struct huffman_node* tree,
                        Bitstream* bitstream);


/*The use case is something like the following:

int alphabet[] = {1, 2, 3, 4};

struct huffman_frequency frequencies[] = {
    {0x1, 1, &alphabet[0]}, // bits 1    correspond to value 1
    {0x1, 2, &alphabet[1]}, // bits 01   correspond to value 2
    {0x1, 3, &alphabet[2]}, // bits 001  correspond to value 3
    {0x0, 3, &alphabet[3]}, // bits 000  correspond to value 4
    {0, 0, NULL}            // list terminator
};

int main(int argc, char* argv[]) {
    struct huffman_node* tree = build_huffman_tree(frequencies);
    Bitstream* bitstream = bs_open(stdin, BS_BIG_ENDIAN);
    int* value;
    int i;

    for (i = 0; i < 8; i++) {
        value = get_huffman_value(tree, bitstream);
        printf("%d ", *value);
    }

    free_huffman_tree(tree);
    bs_close(bitstream);

    return 0;
}

When fed the bytes             0xA4 0x17
which are the big-endian bits  1010 0100 0001 0111
this prints the values         1 2 3 4 3 2 1 1
from our given alphabet.
*/
