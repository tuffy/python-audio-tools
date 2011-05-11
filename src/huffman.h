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

typedef enum {NODE_TREE, NODE_LEAF} huffman_node_type;

struct huffman_node {
    huffman_node_type type;
    union {
        int leaf;
        struct {
            unsigned int id;
            struct bs_huffman_table jump_table[0x200];
            struct huffman_node* bit_0;
            struct huffman_node* bit_1;
        } tree;
    } v;
};

struct byte_bank {
    unsigned int size;
    unsigned int value;
};

/*Takes a list Huffman frequencies and returns a completed Huffman tree.
  The final huffman_frequency in the list should have a length of 0
  and serve as our list terminator.
  The tree must be freed when no longer needed.*/
struct huffman_node* build_huffman_tree(struct huffman_frequency* frequencies);

/*The proper recursive version, probably not to be called directly.*/
struct huffman_node* build_huffman_tree_(unsigned int bits,
                                         unsigned int length,
                                         struct huffman_frequency* frequencies,
                                         unsigned int* counter);

/*Deallocates the space for the Huffman tree*/
void free_huffman_tree(struct huffman_node* node);

int compile_huffman_tree(struct bs_huffman_table (**table)[][0x200],
                         struct huffman_node* tree,
                         bs_endianness endianness);

int compile_huffman_table(struct bs_huffman_table (**table)[][0x200],
                          struct huffman_frequency* frequencies,
                          bs_endianness endianness);

/*returns the total number of rows generated*/
void populate_huffman_tree(struct huffman_node* tree,
                           bs_endianness endianness);

int total_non_leaf_nodes(struct huffman_node* tree);

void transfer_huffman_tree(struct bs_huffman_table (*table)[][0x200],
                           struct huffman_node* tree);

int bank_to_int(struct byte_bank bank);

void next_read_huffman_state(struct bs_huffman_table* state,
                             struct byte_bank bank,
                             struct huffman_node* tree,
                             bs_endianness endianness);

void print_huffman_tree(struct huffman_node* node, int indent);

#endif
