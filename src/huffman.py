#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2012  Brian Langenberger

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import optparse
import json
from bitstream import Byte_Bank,Bitbuffer,last_element


#This takes Huffman code tables in JSON format, like the following:
#
# [[1],       0,
#  [0, 1],    1,
#  [0, 0, 1], 2,
#  [0, 0, 0], 3]
#
#Where the first value in each pair is the leading bits
#and each trailing value is the Huffman value.
#The order of each pair in the list is irrelevent.
#
#It outputs a 2-dimensional array with a variable number of rows,
#each containing 512 columns of bs_huffman_table structs.
#Each row is a non-leaf node in the Huffman tree
#and each column is a bitstream reader context state.
#The value of the bs_table_struct is the next context/next node
#(encoded as a single int, to save space) and/or the final leaf value.
#
#Walking the tree is a simple matter of starting from table[0][context]
#(reading in a new context from the byte stream, if necessary)
#and continuing along table[node][context] until the next node is 0
#before returning the final value.


class Counter:
    def __init__(self):
        self.value = 0

    def __int__(self):
        value = self.value
        self.value += 1
        return value


class Huffman_Node:
    def __init__(self, value=None, bit_0=None, bit_1=None):
        self.value = value
        self.id = 0
        self.bit_0 = bit_0
        self.bit_1 = bit_1

    def is_leaf(self):
        return self.value is not None

    def __repr__(self):
        if (self.value is not None):
            return "Huffman_Node(value=%s)" % (repr(self.value))
        else:
            return "Huffman_Node(bit_0=%s, bit_1=%s)" % \
                (repr(self.bit_0),
                 repr(self.bit_1))

    def enumerate_nodes(self, counter=None):
        if (not self.is_leaf()):
            if (counter is None):
                counter = Counter()
            self.id = int(counter)
            self.bit_0.enumerate_nodes(counter)
            self.bit_1.enumerate_nodes(counter)

    def populate_jump_table(self, little_endian=False):
        if (self.value is None):
            self.jump_table = ([(0, 0, None),   #input context 0
                                (0, 0, None)] + #input context 1
                               [next_read_huffman_state(context.bitbuffer(),
                                                        self,
                                                        little_endian)
                                for context in Byte_Bank.contexts()
                                if (context.size > 0)])
            self.bit_0.populate_jump_table()
            self.bit_1.populate_jump_table()

    def jump_tables(self):
        if (not self.is_leaf()):
            yield (self.id, self.jump_table)
            for table in self.bit_0.jump_tables():
                yield table
            for table in self.bit_1.jump_tables():
                yield table


def build_huffman_tree(frequencies, bits=tuple()):
    if (bits in frequencies):
        return Huffman_Node(value=frequencies[bits])
    else:
        return Huffman_Node(bit_0=build_huffman_tree(frequencies,
                                                     bits + (0,)),
                            bit_1=build_huffman_tree(frequencies,
                                                     bits + (1,)))

def next_read_huffman_state(bit_stream, tree, little_endian):
    if (tree.is_leaf()):
        #reached a leaf node, so return byte bank and node
        return (int(bit_stream.byte_bank()), tree.id, tree.value)
    elif (len(bit_stream) == 0):
        #exhausted byte bank, so return empty bank and node
        return (0, tree.id, None)
    elif (little_endian):
        #progress through bit stream in little-endian order
        if (bit_stream[0]):
            return next_read_huffman_state(bit_stream[1:],
                                           tree.bit_1,
                                           little_endian)
        else:
            return next_read_huffman_state(bit_stream[1:],
                                           tree.bit_0,
                                           little_endian)
    else:
        #progress through bit stream in big-endian order
        if (bit_stream[-1]):
            return next_read_huffman_state(bit_stream[:-1],
                                           tree.bit_1,
                                           little_endian)
        else:
            return next_read_huffman_state(bit_stream[:-1],
                                           tree.bit_0,
                                           little_endian)

def encode_huffman_value(value,
                         next_node,
                         next_context):
    if (value is not None):
        return ("{0x%X, %d}" %
                ((next_node << Byte_Bank.size()) | next_context,
                 value))
    else:
        return ("{0x%X, 0}" %
                ((next_node << Byte_Bank.size()) | next_context))


if (__name__ == '__main__'):
    parser = optparse.OptionParser()

    parser.add_option("-i",
                      dest='input',
                      help='input JSON file')

    parser.add_option('--le',
                      dest='little_endian',
                      action='store_true',
                      default=False,
                      help='generate a little-endian jump table')

    (options, args) = parser.parse_args()

    if (options.input is None):
        print "a JSON file is required"
        sys.exit(1)

    json_data = json.loads(open(options.input, "r").read())
    tree = build_huffman_tree(dict([(tuple(bits), value)
                                    for (bits, value) in
                                    zip(json_data[::2],
                                        json_data[1::2])]))
    tree.enumerate_nodes()
    tree.populate_jump_table(options.little_endian)
    jump_tables = dict(tree.jump_tables())
    print "{"
    for (last_row, row) in last_element([jump_tables[key] for key
                                         in sorted(jump_tables.keys())]):
        print "  {"
        for (last_col, col) in last_element(row):
            (next_context, next_node, value) = col
            sys.stdout.write("    %s" %
                             (encode_huffman_value(value,
                                                   next_node,
                                                   next_context)))
            if (last_col):
                print ""
            else:
                print ","
        if (last_row):
            print "  }"
        else:
            print "  },"
    print "}"
    print >>sys.stderr,"%d rows total" % (len(jump_tables.keys()))
