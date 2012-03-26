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

static struct vorbis_codeword*
codeword_new_leaf(int value, unsigned int length, unsigned int bits);

static struct vorbis_codeword*
codeword_new_tree(void);

static struct vorbis_codeword*
codeword_add_length(struct vorbis_codeword* tree,
                    unsigned int current_depth,
                    unsigned int length,
                    unsigned int bits,
                    int value);

static void
codeword_free_tree(struct vorbis_codeword* tree);

static unsigned int
codeword_total_leaf_nodes(struct vorbis_codeword* tree);

/* static struct huffman_frequency* */
/* codeword_tree_to_frequencies(struct vorbis_codeword* tree); */

/* static void */
/* codeword_tree_to_frequencies_(struct vorbis_codeword* tree, */
/*                               struct huffman_frequency* frequencies, */
/*                               int* index); */
