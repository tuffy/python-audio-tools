#include "huffman.h"
#include <stdlib.h>
#include <string.h>


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

typedef enum {NODE_TREE, NODE_LEAF} huffman_node_type;

struct huffman_node {
    huffman_node_type type;
    union {
        int leaf;
        struct {
            unsigned int id;
            struct br_huffman_table jump_table[0x200];
            struct huffman_node* bit_0;
            struct huffman_node* bit_1;
        } tree;
    } v;
};

#define BYTE_BANK_SIZE 9

struct byte_bank {
    unsigned int size;
    unsigned int value;
};

#define CONTINUE_READING (1 << BYTE_BANK_SIZE)

/*takes a list Huffman frequencies and returns a completed Huffman tree

  the final huffman_frequency in the list should have a length of 0
  and serve as our list terminator

  the tree must be freed when no longer needed*/
static struct huffman_node*
build_huffman_tree(struct huffman_frequency* frequencies,
                   unsigned int total_frequencies,
                   int* error);

/*the proper recursive version, not to be called directly most of the time*/
static struct huffman_node*
build_huffman_tree_(unsigned int bits,
                    unsigned int length,
                    struct huffman_frequency* frequencies,
                    unsigned int total_frequencies,
                    unsigned int* counter,
                    int* error);

/*deallocates the space for the Huffman tree*/
static void
free_huffman_tree(struct huffman_node* node);

/*takes a built Huffman tree and compiles it to a jump table
  with the given endianness*/
static int
compile_huffman_tree(struct br_huffman_table (**table)[][0x200],
                     struct huffman_node* tree,
                     bs_endianness endianness);

/*populates the jump tables of the Huffman tree's nodes*/
static void
populate_huffman_tree(struct huffman_node* tree,
                      bs_endianness endianness);

/*returns the total number of non-leaf nodes in the tree*/
static unsigned int
total_non_leaf_nodes(struct huffman_node* tree);

/*returns the total number of leaf nodes in the tree*/
static unsigned int
total_leaf_nodes(struct huffman_node* tree);

/*transfers the jump tables embedded in the Huffman tree nodes
  to a flattened, 2 dimensional array*/
static void
transfer_huffman_tree(struct br_huffman_table (*table)[][0x200],
                      struct huffman_node* tree);

/*performs the actual walking of the tree

  given a byte bank, endianness and tree,
  updates the jump table with which node the bank will wind up at*/
static void
next_read_huffman_state(struct br_huffman_table* state,
                        struct byte_bank bank,
                        struct huffman_node* tree,
                        bs_endianness endianness);

static void
print_huffman_tree(struct huffman_node* node, int indent);

/*converts the byte bank to a regular integer*/
static int
bank_to_int(struct byte_bank bank);


static int
bank_to_int(struct byte_bank bank) {
    if (bank.size > 0) {
        assert(bank.value <= ((1 << bank.size) - 1));
        return (1 << bank.size) | bank.value;
    } else
        return 0;
}

static struct huffman_node*
build_huffman_tree(struct huffman_frequency* frequencies,
                   unsigned int total_frequencies,
                   int* error)
{
    unsigned int counter = 0;
    struct huffman_node* built_tree;

    built_tree = build_huffman_tree_(0, 0,
                                     frequencies, total_frequencies,
                                     &counter, error);
    if (built_tree != NULL) {
        if (total_frequencies > total_leaf_nodes(built_tree)) {
            *error = HUFFMAN_ORPHANED_LEAF;
            free_huffman_tree(built_tree);
            return NULL;
        } else {
            return built_tree;
        }
    } else {
        return NULL;
    }
}

static struct huffman_node*
build_huffman_tree_(unsigned int bits,
                    unsigned int length,
                    struct huffman_frequency* frequencies,
                    unsigned int total_frequencies,
                    unsigned int* counter,
                    int* error)
{
    unsigned int i;
    unsigned int j;
    struct huffman_node* node = malloc(sizeof(struct huffman_node));
    unsigned int max_frequency_length = 0;

    /*go through the list of frequency values*/
    for (i = 0; i < total_frequencies; i++) {
        /*if our bits and length value is found,
          generate a new leaf node from that frequency
          so long as it is unique in the list*/
        if ((frequencies[i].bits == bits) &&
            (frequencies[i].length == length)) {
            /*check for duplicates*/
            for (j = i + 1; j < total_frequencies; j++) {
                if ((frequencies[j].bits == bits) &&
                    (frequencies[j].length == length)) {
                    *error = HUFFMAN_DUPLICATE_LEAF;
                    free(node);
                    return NULL;
                }
            }

            node->type = NODE_LEAF;
            node->v.leaf = frequencies[i].value;
            return node;
        } else {
            max_frequency_length = MAX(max_frequency_length,
                                       frequencies[i].length);
        }
    }

    if (length > max_frequency_length) {
        /*we've walked outside of the set of possible frequencies
          which indicates the tree is missing a leaf node*/
        *error = HUFFMAN_MISSING_LEAF;
        free(node);
        return NULL;
    }

    /*otherwise, generate a new tree node
      whose leaf nodes are generated recursively*/
    node->type = NODE_TREE;
    node->v.tree.id = *counter;
    node->v.tree.bit_0 = NULL;
    node->v.tree.bit_1 = NULL;
    (*counter) += 1;
    if ((node->v.tree.bit_0 = build_huffman_tree_(bits << 1,
                                                  length + 1,
                                                  frequencies,
                                                  total_frequencies,
                                                  counter,
                                                  error)) == NULL)
        goto error;

    if ((node->v.tree.bit_1 = build_huffman_tree_((bits << 1) | 1,
                                                  length + 1,
                                                  frequencies,
                                                  total_frequencies,
                                                  counter,
                                                  error)) == NULL)
        goto error;

    return node;
 error:
    free_huffman_tree(node->v.tree.bit_0);
    free_huffman_tree(node->v.tree.bit_1);
    free(node);
    return NULL;
}

static void
free_huffman_tree(struct huffman_node* node) {
    if (node == NULL)
        return;
    else if (node->type == NODE_LEAF) {
        free(node);
    } else {
        free_huffman_tree(node->v.tree.bit_0);
        free_huffman_tree(node->v.tree.bit_1);
        free(node);
    }
}

void print_huffman_tree(struct huffman_node* node, int indent) {
    int i;
    for (i = 0; i < indent; i++) {
        printf(" ");
    }
    switch (node->type) {
    case NODE_LEAF:
        printf("leaf : %d\n", node->v.leaf);
        break;
    case NODE_TREE:
        printf("node (%u)\n", node->v.tree.id);
        print_huffman_tree(node->v.tree.bit_0, indent + 2);
        print_huffman_tree(node->v.tree.bit_1, indent + 2);
    }
}

static int
compile_huffman_tree(struct br_huffman_table (**table)[][0x200],
                     struct huffman_node* tree,
                     bs_endianness endianness) {
    int total_rows = total_non_leaf_nodes(tree);
    unsigned int size;
    unsigned int value;
    struct byte_bank bank;
    int bank_int;

    if (total_rows > 0) {
        /*populate the jump tables of each non-leaf node*/
        populate_huffman_tree(tree, endianness);

        /*allocate space for the entire set of jump tables*/
        *table = malloc(sizeof(struct br_huffman_table) * total_rows * 0x200);

        /*transfer jump tables of each node from tree*/
        transfer_huffman_tree(*table, tree);
    } else if (total_leaf_nodes(tree) > 0) {
        /*no non-leaf nodes, so the table is trivial
          all inputs consume no bits and return the final value*/

        *table = malloc(sizeof(struct br_huffman_table) * 1 * 0x200);

        (**table)[0][0].context_node = 0;
        (**table)[0][0].value = tree->v.leaf;
        (**table)[0][1].context_node = 0;
        (**table)[0][1].value = tree->v.leaf;
        for (size = 1; size < (8 + 1); size++)
            for (value = 0; value < (1 << size); value++) {
                bank.size = size;
                bank.value = value;
                bank_int = bank_to_int(bank);

                (**table)[0][bank_int].context_node = bank_int;
                (**table)[0][bank_int].value = tree->v.leaf;
            }

        total_rows = 1;
    } else {
        *table = malloc(0);
        return HUFFMAN_EMPTY_TREE;
    }

    return total_rows;
}

static void
populate_huffman_tree(struct huffman_node* tree,
                      bs_endianness endianness) {
    unsigned int size;
    unsigned int value;
    struct byte_bank bank;

    if (tree->type == NODE_TREE) {
        tree->v.tree.jump_table[0].context_node = CONTINUE_READING;
        tree->v.tree.jump_table[0].value = 0;
        tree->v.tree.jump_table[1].context_node = CONTINUE_READING;
        tree->v.tree.jump_table[1].value = 0;

        for (size = 1; size < (8 + 1); size++)
            for (value = 0; value < (1 << size); value++) {
                bank.size = size;
                bank.value = value;

                next_read_huffman_state(
                    &(tree->v.tree.jump_table[bank_to_int(bank)]),
                    bank, tree, endianness);
        }

        populate_huffman_tree(tree->v.tree.bit_0, endianness);
        populate_huffman_tree(tree->v.tree.bit_1, endianness);
    }
}

void next_read_huffman_state(struct br_huffman_table* state,
                             struct byte_bank bank,
                             struct huffman_node* tree,
                             bs_endianness endianness) {
    struct byte_bank next_bank;

    if (tree->type == NODE_LEAF) {
        /*reached a leaf node,
          so return current byte bank, empty continue bit and value*/
        state->context_node = bank_to_int(bank);
        state->value = tree->v.leaf;
    } else if (bank.size == 0) {
        /*exhausted byte bank,
          so return empty bank, set continue bit and current node*/
        state->context_node = ((tree->v.tree.id << (BYTE_BANK_SIZE + 1)) |
                               CONTINUE_READING);
        state->value = 0;
    } else if (endianness == BS_LITTLE_ENDIAN) {
        /*progress through bit stream in little endian order*/
        next_bank = bank;
        next_bank.size -= 1;
        next_bank.value >>= 1;

        if (bank.value & 1) {
            next_read_huffman_state(state,
                                    next_bank,
                                    tree->v.tree.bit_1,
                                    endianness);
        } else {
            next_read_huffman_state(state,
                                    next_bank,
                                    tree->v.tree.bit_0,
                                    endianness);

        }
    } else if (endianness == BS_BIG_ENDIAN) {
        /*progress through bit stream in big endian order*/
        next_bank = bank;
        next_bank.size -= 1;
        next_bank.value &= ((1 << next_bank.size) - 1);

        if (bank.value & (1 << (bank.size - 1))) {
            next_read_huffman_state(state,
                                    next_bank,
                                    tree->v.tree.bit_1,
                                    endianness);
        } else {
            next_read_huffman_state(state,
                                    next_bank,
                                    tree->v.tree.bit_0,
                                    endianness);

        }
    }
}

static unsigned int
total_non_leaf_nodes(struct huffman_node* tree) {
    if (tree->type == NODE_TREE) {
        return (1 +
                total_non_leaf_nodes(tree->v.tree.bit_0) +
                total_non_leaf_nodes(tree->v.tree.bit_1));
    } else
        return 0;
}

static unsigned int
total_leaf_nodes(struct huffman_node* tree) {
    if (tree->type == NODE_TREE) {
        return (total_leaf_nodes(tree->v.tree.bit_0) +
                total_leaf_nodes(tree->v.tree.bit_1));
    } else
        return 1;
}

static void
transfer_huffman_tree(struct br_huffman_table (*table)[][0x200],
                      struct huffman_node* tree) {
    int i;

    if (tree->type == NODE_TREE) {
        /*not sure if this can be made more efficient*/
        for (i = 0; i < 0x200; i++) {
            (*table)[tree->v.tree.id][i] = tree->v.tree.jump_table[i];
        }
        transfer_huffman_tree(table, tree->v.tree.bit_0);
        transfer_huffman_tree(table, tree->v.tree.bit_1);
    }
}

int compile_huffman_table(struct br_huffman_table (**table)[][0x200],
                          struct huffman_frequency* frequencies,
                          unsigned int total_frequencies,
                          bs_endianness endianness) {
    int error = 0;
    struct huffman_node* tree;
    int total_rows;

    tree = build_huffman_tree(frequencies, total_frequencies, &error);
    if (tree == NULL)
        return error;
    total_rows = compile_huffman_tree(table, tree, endianness);
    free_huffman_tree(tree);
    return total_rows;
}

#ifdef EXECUTABLE

#include <jansson.h>
#include <getopt.h>

struct huffman_frequency* json_to_frequencies(const char* path,
                                              unsigned int* total_frequencies);

struct huffman_frequency parse_json_pair(json_t* bit_list, json_t* value);

int main(int argc, char* argv[]) {
    /*option handling variables*/
    static int little_endian_arg = 0;
    bs_endianness little_endian;
    char* input_file = NULL;

    static struct option long_options[] = {
        {"input", required_argument, 0, 'i'},
        {"help", no_argument, 0, 'h'},
        {"le", no_argument, &little_endian_arg, 1},
        {0, 0, 0, 0}
    };

    int option_index = 0;
    int c;

    /*the variables for real work*/
    struct huffman_frequency* frequencies;
    unsigned int total_frequencies;
    struct br_huffman_table (*table)[][0x200];
    int row;
    int context;
    int total_rows;

    do {
        c = getopt_long(argc, argv, "i:h", long_options, &option_index);
        switch (c) {
        case 'h':
            printf("Options:\n");
            printf("  -h, --help             "
                   "show this help message and exit\n");
            printf("  -i PATH, --input=PATH  "
                   "input JSON file\n");
            printf("  --le                   "
                   "generate little-endian jump table\n");
            return 0;
        case 'i':
            input_file = optarg;
            break;
        case '?':
            return 1;
        case 0:
        case -1:
        default:
            break;
        }
    } while (c != -1);

    if (input_file == NULL) {
        fprintf(stderr, "an input file is required\n");
        return 1;
    }

    little_endian = little_endian_arg ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN;

    frequencies = json_to_frequencies(input_file, &total_frequencies);

    total_rows = compile_huffman_table(&table, frequencies, total_frequencies,
                                       little_endian);
    if (total_rows < 0)
        switch (total_rows) {
        case HUFFMAN_MISSING_LEAF:
            fprintf(stderr, "Huffman table missing leaf node\n");
            free(frequencies);
            return 1;
        case HUFFMAN_DUPLICATE_LEAF:
            fprintf(stderr, "Huffman table has duplicate leaf node\n");
            free(frequencies);
            return 1;
        case HUFFMAN_ORPHANED_LEAF:
            fprintf(stderr, "Huffman table has orphaned leaf nodes\n");
            free(frequencies);
            return 1;
        default:
            fprintf(stderr, "Unknown error\n");
            free(frequencies);
            return 1;
        }

    printf("{\n");
    for (row = 0; row < total_rows; row++) {
        printf("  {\n");

        for (context = 0; context < 0x200; context++) {
            printf("    {0x%X, %d}",
                   (*table)[row][context].context_node,
                   (*table)[row][context].value);
            if (context < (0x200 - 1))
                printf(",\n");
            else
                printf("\n");
        }
        if (row < (total_rows - 1))
            printf("  },\n");
        else
            printf("  }\n");
    }
    printf("}\n");

    free(table);
    free(frequencies);
    return 0;
}

struct huffman_frequency* json_to_frequencies(const char* path,
                                              unsigned int* total_frequencies) {
    json_error_t error;
    json_t* input = json_load_file(path, 0, &error);
    size_t input_size;
    int o;
    size_t i;
    struct huffman_frequency* frequencies;

    if (input == NULL) {
        fprintf(stderr, "%s %d: %s\n", error.source, error.line, error.text);
        exit(1);
    }

    input_size = json_array_size(input);

    frequencies = malloc(sizeof(struct huffman_frequency) *
                         (input_size / 2));

    *total_frequencies = input_size / 2;
    for (i = o = 0; i < input_size; i += 2,o++) {
        frequencies[o] = parse_json_pair(json_array_get(input, i),
                                         json_array_get(input, i + 1));
    }

    json_decref(input);

    return frequencies;
}

struct huffman_frequency parse_json_pair(json_t* bit_list, json_t* value) {
    struct huffman_frequency frequency;
    size_t i;

    frequency.bits = 0;
    frequency.length = 0;

    for (i = 0; i < json_array_size(bit_list); i++) {
        frequency.bits = ((frequency.bits << 1) |
                          json_integer_value(json_array_get(bit_list, i)));
        frequency.length++;
    }

    frequency.value = json_integer_value(value);

    return frequency;
}

#endif
