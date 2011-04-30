#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

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
# {"val[0]":[1],
#  "val[1]":[0, 1],
#  "val[2]":[0, 0, 1],
#  "val[3]":[0, 0, 0]}
#
#in which the key is a unique C pointer value
#and the value is a list of leading bits.
#It compiles that Huffman table into a C jump table
#suitable for #including in a C program
#which will then pass to the Bitstream->read_huffman_code function.
#
#I may need to swap this around such that the bits comprise the key
#rather than the end value, which may not be unique.

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
            self.jump_table = [next_read_huffman_state(context.bitbuffer(),
                                                       self,
                                                       little_endian)
                               for context in Byte_Bank.contexts()]
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


if (__name__ == '__main__'):
    parser = optparse.OptionParser()

    parser.add_option("-i",
                      dest='input',
                      help='input JSON file')

    (options, args) = parser.parse_args()

    if (options.input is None):
        print "a JSON file is required"
        sys.exit(1)

    frequencies = dict([(tuple(value), key)
                        for (key, value) in
                        json.loads(open(options.input, "r").read()).items()])
    tree = build_huffman_tree(frequencies)
    tree.enumerate_nodes()
    tree.populate_jump_table()
    jump_tables = dict(tree.jump_tables())
    print "{"
    for (last_row, row) in last_element(
        zip(*[jump_tables[key] for key in sorted(jump_tables.keys())])):
        for (last_col, col) in last_element(row):
            (next_context, next_node, value) = col
            if (value is not None):
                sys.stdout.write("  {0x%X, %d, &%s}" %
                                 (next_context, next_node,
                                  value.encode('ascii')))
            else:
                sys.stdout.write("  {0x%X, %d, NULL}" %
                                 (next_context, next_node))
            if (last_row and last_col):
                print ""
            else:
                print ","
    print "}"
    print >>sys.stderr,"%d columns total" % (len(jump_tables.keys()))
