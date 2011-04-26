#include "huffman.h"
#include <stdlib.h>


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

struct huffman_node* build_huffman_tree(struct huffman_frequency* frequencies)
{
    return build_huffman_tree_(0, 0, frequencies);
}

struct huffman_node* build_huffman_tree_(unsigned int bits,
                                         unsigned int length,
                                         struct huffman_frequency* frequencies)
{
    int i;
    struct huffman_node* node = malloc(sizeof(struct huffman_node));

    /*go through the list of frequency values*/
    for (i = 0; frequencies[i].length != 0; i++) {
        /*if our bits and length value is found,
          generate a new leaf node from that frequency*/
        if ((frequencies[i].bits == bits) &&
            (frequencies[i].length == length)) {
            node->type = NODE_LEAF;
            node->v.leaf = frequencies[i].value;
            return node;
        }
    }

    /*otherwise, generate a new tree node
      whose leaf nodes are generated recursively*/
    node->type = NODE_TREE;
    node->v.tree.bit_0 = build_huffman_tree_(bits << 1,
                                             length + 1,
                                             frequencies);
    node->v.tree.bit_1 = build_huffman_tree_((bits << 1) | 1,
                                             length + 1,
                                             frequencies);
    return node;
}

void free_huffman_tree(struct huffman_node* node) {
    if (node->type == NODE_LEAF) {
        free(node);
    } else {
        free_huffman_tree(node->v.tree.bit_0);
        free_huffman_tree(node->v.tree.bit_1);
        free(node);
    }
}

void* get_huffman_value(struct huffman_node* tree,
                        Bitstream* bitstream) {
    while (tree->type == NODE_TREE) {
        if (bitstream->read(bitstream, 1)) {
            tree = tree->v.tree.bit_1;
        } else {
            tree = tree->v.tree.bit_0;
        }
    }

    return tree->v.leaf;
}
