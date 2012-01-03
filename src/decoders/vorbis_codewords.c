/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

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

/*codeword helper functions for transforming
  the list of frequencies into a proper Huffman lookup table*/
static struct vorbis_codeword*
codeword_new_leaf(int value, unsigned int length, unsigned int bits) {
    struct vorbis_codeword* leaf = malloc(sizeof(struct vorbis_codeword));
    leaf->is_leaf = 1;
    leaf->value = value;
    leaf->bits = bits;
    leaf->length = length;
    return leaf;
}

static struct vorbis_codeword*
codeword_new_tree(void) {
    struct vorbis_codeword* tree = malloc(sizeof(struct vorbis_codeword));
    tree->is_leaf = 0;
    tree->bit_0 = NULL;
    tree->bit_1 = NULL;
    return tree;
}

static void
codeword_free_tree(struct vorbis_codeword* tree) {
    if (tree == NULL) {
        return;
    } else if (tree->is_leaf) {
        free(tree);
    } else {
        codeword_free_tree(tree->bit_0);
        codeword_free_tree(tree->bit_1);
        free(tree);
    }
}

static unsigned int
codeword_total_leaf_nodes(struct vorbis_codeword* tree) {
    if (tree == NULL) {
        return 0;
    } else if (tree->is_leaf) {
        return 1;
    } else {
        return (codeword_total_leaf_nodes(tree->bit_0) +
                codeword_total_leaf_nodes(tree->bit_1));
    }
}

static struct vorbis_codeword*
codeword_add_length(struct vorbis_codeword* tree,
                    unsigned int current_depth,
                    unsigned int length,
                    unsigned int bits,
                    int value) {
    struct vorbis_codeword* new_leaf;

    if (current_depth == length) {
        if (tree != NULL)
            /*node already present, so return failure*/
            return NULL;
        else
            /*node not yet present, so add new node*/
            return codeword_new_leaf(value, length, bits);
    } else if (current_depth < length) {
        if (tree != NULL) {
            if (tree->is_leaf) {
                /*can't add leaf nodes to other leaves*/
                return NULL;
            } else {
                /*try bit 0 first*/
                new_leaf = codeword_add_length(tree->bit_0,
                                               current_depth + 1,
                                               length,
                                               bits << 1,
                                               value);
                if (new_leaf != NULL) {
                    tree->bit_0 = new_leaf;
                    return tree;
                }

                /*then try the 1 bit*/
                new_leaf = codeword_add_length(tree->bit_1,
                                               current_depth + 1,
                                               length,
                                               (bits << 1) | 1,
                                               value);
                if (new_leaf != NULL) {
                    tree->bit_1 = new_leaf;
                    return tree;
                }

                /*if neither works, return failure*/
                return NULL;
            }
        } else {
            /*tree not yet large enough, so add new non-leaf node*/
            tree = codeword_new_tree();
            tree->bit_0 = codeword_add_length(tree->bit_0,
                                              current_depth + 1,
                                              length,
                                              bits << 1,
                                              value);
            return tree;
        }
    } else {
        /*walked too far within tree, so return failure*/
        return NULL;
    }
}

static struct huffman_frequency*
codeword_tree_to_frequencies(struct vorbis_codeword* tree) {
    struct huffman_frequency* frequencies =
        malloc(sizeof(struct huffman_frequency) *
               (codeword_total_leaf_nodes(tree) + 1));
    int index = 0;

    codeword_tree_to_frequencies_(tree, frequencies, &index);
    frequencies[index].length = 0;
    return frequencies;
}

static void
codeword_tree_to_frequencies_(struct vorbis_codeword* tree,
                              struct huffman_frequency* frequencies,
                              int* index) {
    if (tree == NULL) {
        return;
    } else if (tree->is_leaf) {
        frequencies[*index].value = tree->value;
        frequencies[*index].bits = tree->bits;
        frequencies[*index].length = tree->length;
        *index += 1;
    } else {
        codeword_tree_to_frequencies_(tree->bit_0,
                                      frequencies,
                                      index);
        codeword_tree_to_frequencies_(tree->bit_1,
                                      frequencies,
                                      index);
    }
}
