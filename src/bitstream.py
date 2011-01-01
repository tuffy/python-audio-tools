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


#this is a list-like class that stores the least significant bits
#at position 0 in the array and most significant bits further up
class Bitbuffer(list):
    #takes a list of bits or an integer value
    def __init__(self, args):
        if (not hasattr(args,"__iter__")):
            integer = int(args)
            args = []
            while (integer > 0):
                args.append(integer & 1)
                integer >>= 1
            list.__init__(self,args)
        else:
            list.__init__(self,args)

    #returns a representation with the least-significant bit on the right
    #*this is the exact opposite of how list(Bitbuffer([1,1,0]))
    # (for the value 3) will display data!*
    #but is more in line with my expectations
    def __repr__(self):
        lsb_on_right = list(self)
        lsb_on_right.reverse()
        return "Bitbuffer(%s)" % \
            (repr(lsb_on_right))

    #returns the Bitbuffer's data as an integer
    def __int__(self):
        accumulator = 0
        for (i,b) in enumerate(self):
            accumulator |= (b << i)
        return accumulator

    #though this is deprecated,
    #I want slices of Bitbuffers to return more Bitbuffers
    def __getslice__(self, i, j):
        return Bitbuffer(list.__getslice__(self,i,j))

    #takes a set of lower-significance bits and appends our data to the end
    def __add__(self,least_significant_bitbuffer):
        return Bitbuffer(list(least_significant_bitbuffer) + list(self))

    def copy(self):
        return Bitbuffer(list(self))

    def pad(self, total_bits):
        while (len(self) < total_bits):
            self.append(0)


#incoming context is:
#4 bits - byte bank size (from 0 to 8)
#8 bits - byte bank value (from 0x00 to 0xFF)
#
#returns an array of 8 integers
#that array's index is the amount of bits we're reading
#where 0-7 corresponds to reading 1 to 8 bits
#
#the value in the array is a 24-bit, multiplexed pair of items:
#4 bits  - returned value size (from 0 to 8)
#8 bits  - returned value (from 0x00 to 0xFF)
#12 bits - next context
#the returned value size may be smaller than the requested number of bits
#which means another call will be required to get the full result
def next_read_bits_states(context):
    for bits_requested in xrange(1,9):
        byte_bank = Bitbuffer(context & 0xFF);
        byte_bank.pad(context >> 8)

        #chop off the top "bits_requested" bits from the bank
        returned_bits = byte_bank[-bits_requested:]

        #use the remaining bits in the bank as our next state
        byte_bank = byte_bank[0:-bits_requested]

        #yield the combination of return value and next state
        yield (len(returned_bits) << 20) | \
            (int(returned_bits) << 12) | \
            (len(byte_bank) << 8) | \
            int(byte_bank)

#identical to the previous, but delivers least-significant bits first
def next_read_bits_states_le(context):
    for bits_requested in xrange(1,9):
        byte_bank = Bitbuffer(context & 0xFF);
        byte_bank.pad(context >> 8)

        #chop off the bottom "bits_requested" bits from the bank
        returned_bits = byte_bank[:bits_requested]

        #use the remaining bits in the bank as our next state
        byte_bank = byte_bank[bits_requested:]

        #yield the combination of return value and next state
        yield (len(returned_bits) << 20) | \
            (int(returned_bits) << 12) | \
            (len(byte_bank) << 8) | \
            int(byte_bank)

#incoming context is
#4 bits - byte bank size (from 0 to 8)
#8 bits - byte bank value (from 0x00 to 0xFF)
#
#returns an array of 2 integers
#that array's index is bit we're un-reading, either 0 or 1
#
#the value in the array is a 13-bit, multiplexed set of items:
#1 bit   - unable to unread any more bits
#12 bits - next context
#although we should always be able to unread at least 1 bit
#(getting 1 bit from a 0x000 context results in reading a whole byte
# before shifting the context to 0x7xx, for example, which means we
# can unread 1 bit back to 0x8xx)
#but more than 1 may not be possible
def next_unread_bit_states(context):
    for unread_bit in xrange(2):
        byte_bank = Bitbuffer(context & 0xFF);
        byte_bank.pad(context >> 8)

        if (len(byte_bank) < 8):
            byte_bank.append(unread_bit)
            yield (len(byte_bank) << 8) | \
                int(byte_bank)
        else:
            yield (1 << 12) | \
                (len(byte_bank) << 8) | \
                int(byte_bank)

#like the previous, but prepends the bit instead of appending it
def next_unread_bit_states_le(context):
    for unread_bit in xrange(2):
        byte_bank = Bitbuffer(context & 0xFF);
        byte_bank.pad(context >> 8)

        if (len(byte_bank) < 8):
            byte_bank.insert(0, unread_bit)
            yield (len(byte_bank) << 8) | \
                int(byte_bank)
        else:
            yield (1 << 12) | \
                (len(byte_bank) << 8) | \
                int(byte_bank)


#incoming context is the same as in next_read_bits_states:
#4 bits - byte bank size (from 0 to 8)
#8 bits - byte bank value (from 0x00 to 0xFF)
#
#returns an array of 2 integers
#that array's index is whether we stop at a 0 bit, or a 1 bit (in that order)
#
#the value in the array is a 17-bit, multiplexed triple of items:
#1 bit   - continue reading
#4 bits  - returned value (from 0 to 8)
#12 bits - next context
#if the topmost bit is set, it means we've exhausted the bank
#without hitting a stop bit, and must continue to another byte
#for example, if our bank is 0x800 (8, zero bits) and we stop at 1,
#the value 0x18000 is returned
def next_read_unary_states(context):
    for stop_bit in xrange(0,2):
        byte_bank = Bitbuffer(context & 0xFF);
        byte_bank.pad(context >> 8)

        #why reversed?
        #remember, we're reading the bitstream from left to right
        #or most-significant bit to least-significant bit
        for (count,bit) in enumerate(reversed(byte_bank)):
            if (bit == stop_bit):
                #the total number bits we've skipped is the returned value

                #what's left over is our next state
                byte_bank = byte_bank[:len(byte_bank) - count - 1]

                yield ((count << 12) |
                       (len(byte_bank) << 8) |
                       int(byte_bank))
                break
        else:
            #unless we don't find the stop bit,
            #in which case we need to send a continue
            yield ((1 << 16) |
                   ((count + 1) << 12))

#same as above, but pulls from least-significant bits first
def next_read_unary_states_le(context):
    for stop_bit in xrange(0,2):
        byte_bank = Bitbuffer(context & 0xFF);
        byte_bank.pad(context >> 8)

        for (count,bit) in enumerate(byte_bank):
            if (bit == stop_bit):
                #the total number bits we've skipped is the returned value

                #what's left over is our next state
                byte_bank = byte_bank[count + 1:]

                yield ((count << 12) |
                       (len(byte_bank) << 8) |
                       int(byte_bank))
                break
        else:
            #unless we don't find the stop bit,
            #in which case we need to send a continue
            yield ((1 << 16) |
                   ((count + 1) << 12))

#incoming context is the same as in next_read_bits_states:
#4 bits - byte bank size (from 0 to 8)
#8 bits - byte bank value (from 0x00 to 0xFF)
#
#returns an array of 18 integers
#the first 9 are when we stop at a 0 bit, and a maximum of 0-8 bits
#the next 9 are when we stop at a 1 bit, and a maximum of 0-8 bits
#
#the value in the array is an 18-bit, multiplexed quad of items:
#1 bit   - maximum value reached
#1 bit   - continue reading
#4 bits  - returned value (from 0 to 8)
#12 bits - next context
#if the "continue reading" bit is set, it means we've exhausted the bank
#without hitting a stop bit, and must continue to another byte
#if the "maximum value reached" bit is set, it means we've hit the
#maximum number of bits to read
def next_read_limited_unary_states(context):
    for state in xrange(0, 18):
        stop_bit = state / 9
        maximum_value = state % 9
        byte_bank = Bitbuffer(context & 0xFF)
        byte_bank.pad(context >> 8)

        #read the bitstream from left to right
        #or most-significant to least-significant
        for (count, bit) in enumerate(reversed(byte_bank)):
            if (count >= maximum_value):
                #what's left is our next state
                byte_bank = byte_bank[:len(byte_bank) - count]

                yield ((1 << 17) |
                       (len(byte_bank) << 8) |
                       int(byte_bank))
                break
            elif (bit == stop_bit):
                #the total number of bits skipped is the return value
                value = count

                #what's left is our next state
                byte_bank = byte_bank[:len(byte_bank) - count - 1]

                yield ((count << 12) |
                       (len(byte_bank) << 8) |
                       int(byte_bank))
                break
        else:
            #unless we don't find the stop bit,
            #in which case we need to send a continue
            returned_bits = count + 1
            yield ((1 << 16) |
                   ((count + 1) << 12))

#same as previous, but in little-endian order
def next_read_limited_unary_states_le(context):
    for state in xrange(0, 18):
        stop_bit = state / 9
        maximum_value = state % 9
        byte_bank = Bitbuffer(context & 0xFF)
        byte_bank.pad(context >> 8)

        #read the bitstream from right to left
        #or least-significant to most-significant
        for (count, bit) in enumerate(byte_bank):
            if (count >= maximum_value):
                #what's left is our next state
                byte_bank = byte_bank[count:]

                yield ((1 << 17) |
                       (len(byte_bank) << 8) |
                       int(byte_bank))
                break
            elif (bit == stop_bit):
                #the total number of bits skipped is the return value
                value = count

                #what's left is our next state
                byte_bank = byte_bank[count + 1:]

                yield ((count << 12) |
                       (len(byte_bank) << 8) |
                       int(byte_bank))
                break
        else:
            #unless we don't find the stop bit,
            #in which case we need to send a continue
            returned_bits = count + 1
            yield ((1 << 16) |
                   ((count + 1) << 12))

#incoming context is:
#3 bits - byte bank size (from 0 to 7)
#7 bits - byte bank value (from 0x00 to 0x7F)
#this is 1 bit smaller than the read_bits context, above
#because once we hit 8 bits, a full byte should be written to disk
#
#returns an array of 0x900 (2048) values
#that array corresponds to a multiplexed value we're writing
#from 0x100 (writing a single, zero bit) to 0x8FF (writing eight, one bits)
#
#the value in the array is a 19-bit, multiplexed triple of items:
#1 bit   - perform byte writing
#8 bits  - byte to write to disk
#10 bits - next context
#(this is smaller than read_bits' value because the output byte
# is always a constant 8-bit size, whereas read_bits' varies)
def next_write_bits_states(context):
    for wrote_context in xrange(0x8FF + 1):
        #note that the vertical context is only 10 bits wide
        #3 for bank_size
        #7 for the byte_bank
        #unlike when reading, writing involves a byte-write call
        #every 8 bits, so the context need not be as large

        byte_bank = Bitbuffer(context & 0x7F)
        byte_bank.pad(context >> 7)

        wrote_bits = wrote_context >> 8
        wrote_bank = Bitbuffer(wrote_context & ((1 << wrote_bits) - 1))
        wrote_bank.pad(wrote_bits)

        #add our newly wrote bits to the beginning of the byte bank
        new_bank =  byte_bank + wrote_bank

        #if we have more than 8 bits in the bank,
        #generate a write request and new context
        if (len(new_bank) >= 8):
            write_byte = int(new_bank[-8:])
            new_bank = new_bank[0:-8]

            yield (1 << 18) | \
                (write_byte << 10) | \
                (len(new_bank) << 7) | \
                (int(new_bank))
        else:
            #otherwise, just generate a new context
            yield (len(new_bank) << 7) | int(new_bank)

#same as above, but wrote bits are sent to the opposite side
def next_write_bits_states_le(context):
    for wrote_context in xrange(0x8FF + 1):
        #note that the vertical context is only 10 bits wide
        #3 for bank_size
        #7 for the byte_bank
        #unlike when reading, writing involves a byte-write call
        #every 8 bits, so the context need not be as large

        byte_bank = Bitbuffer(context & 0x7F)
        byte_bank.pad(context >> 7)

        wrote_bits = wrote_context >> 8
        wrote_bank = Bitbuffer(wrote_context & ((1 << wrote_bits) - 1))
        wrote_bank.pad(wrote_bits)

        #add our newly wrote bits to the end of the byte bank
        new_bank = wrote_bank + byte_bank

        #if we have more than 8 bits in the bank,
        #generate a write request and new context
        if (len(new_bank) >= 8):
            write_byte = int(new_bank[0:8])
            new_bank = new_bank[8:]

            yield (1 << 18) | \
                (write_byte << 10) | \
                (len(new_bank) << 7) | \
                (int(new_bank))
        else:
            #otherwise, just generate a new context
            yield (len(new_bank) << 7) | int(new_bank)

#incoming context is the same as in next_write_bits_states:
#3 bits - byte bank size (from 0 to 7)
#7 bits - byte bank value (from 0x00 to 0x7F)
#
#returns an array of 32 values
#that array's index corresponds to a multiplexed value we're writing
#1 bit  - our stop bit, either 0 or 1
#1 bit  - the continuation bit
#3 bits - the value we're writing, from 0 to 7
#the continuation bit is for writing single values over 7 bits long
#if set, a full set of continuation bits are sent
#(for example, to write the value 8 in with stop bit 1,
# we send 0x18 followed by 0x10)
#
#the value in the array is a 19-bit, multiplexed triple of items:
#1 bit   - perform byte writing
#8 bits  - byte to write to disk
#10 bits - next context
#again, this is identical to write_bits' return value
def next_write_unary_states(context):
    for wrote_array in xrange(0x1F + 1):
        byte_bank = Bitbuffer(context & 0x7F)
        byte_bank.pad(context >> 7)

        stop_bit = wrote_array >> 4
        continue_bit = (wrote_array >> 3) & 0x01
        wrote_value = wrote_array & 0x07

        #transform our straight bits into unary bits
        if (continue_bit == 0):
            wrote_bank = Bitbuffer([stop_bit] +
                                   ([stop_bit ^ 1] * wrote_value))
        else:
            wrote_bank = Bitbuffer([stop_bit ^ 1] * 8)

        #add our newly wrote bits to the beginning of the byte bank
        new_bank = byte_bank + wrote_bank

        #if we have more than 8 bits in the bank,
        #generate a write request and new context
        if (len(new_bank) >= 8):
            write_byte = int(new_bank[-8:])
            new_bank = new_bank[0:-8]

            yield (1 << 18) | \
                (write_byte << 10) | \
                (len(new_bank) << 7) | \
                (int(new_bank))
        else:
            #otherwise, just generate a new context
            yield (len(new_bank) << 7) | int(new_bank)

#same as previous, but new bytes go on the other end of the bank
def next_write_unary_states_le(context):
    for wrote_array in xrange(0x1F + 1):
        byte_bank = Bitbuffer(context & 0x7F)
        byte_bank.pad(context >> 7)

        stop_bit = wrote_array >> 4
        continue_bit = (wrote_array >> 3) & 0x01
        wrote_value = wrote_array & 0x07

        #transform our straight bits into unary bits
        if (continue_bit == 0):
            wrote_bank = Bitbuffer(([stop_bit ^ 1] * wrote_value) +
                                   [stop_bit])
        else:
            wrote_bank = Bitbuffer([stop_bit ^ 1] * 8)

        #add our newly wrote bits to the end of the byte bank
        new_bank = wrote_bank + byte_bank

        #if we have more than 8 bits in the bank,
        #generate a write request and new context
        if (len(new_bank) >= 8):
            write_byte = int(new_bank[:8])
            new_bank = new_bank[8:]

            yield (1 << 18) | \
                (write_byte << 10) | \
                (len(new_bank) << 7) | \
                (int(new_bank))
        else:
            #otherwise, just generate a new context
            yield (len(new_bank) << 7) | int(new_bank)


def states(minimum_bits=1,maximum_bits=8):
    for bank_size in reversed(range(minimum_bits,maximum_bits + 1)):
        for byte in range(0,1 << bank_size):
            yield (bank_size << maximum_bits) | byte

def int_row(ints,last):
    if (not last):
        return "{" + (",".join(["0x%X" % (i) for i in ints])) + "},\n"
    else:
        return "{" + (",".join(["0x%X" % (i) for i in ints])) + "}\n"

def last_element(iterator):
    iterator = iter(iterator)
    previous = iterator.next()

    try:
        while (True):
            next = iterator.next()
            yield (False,previous)
            previous = next
    except StopIteration:
        yield (True,previous)

if (__name__ == '__main__'):
    parser = optparse.OptionParser()

    parser.add_option('--rb',
                      dest='read_bits',
                      action='store_true',
                      default=False,
                      help='create read bits jump table')

    parser.add_option('--urb',
                      dest='unread_bit',
                      action='store_true',
                      default=False,
                      help='create unread bit jump table')

    parser.add_option('--wb',
                      dest='write_bits',
                      action='store_true',
                      default=False,
                      help='create write bits jump table')

    parser.add_option('--ru',
                      dest='read_unary',
                      action='store_true',
                      default=False,
                      help='create read unary jump table')

    parser.add_option('--rlu',
                      dest='read_limited_unary',
                      action='store_true',
                      default=False,
                      help='created read limited unary jump table')

    parser.add_option('--wu',
                      dest='write_unary',
                      action='store_true',
                      default=False,
                      help='create write unary jump table')

    parser.add_option('--le',
                      dest='little_endian',
                      action='store_true',
                      default=False,
                      help='generate a little-endian jump table')

    (options,args) = parser.parse_args()

    if (options.read_bits):
        if (not options.little_endian):
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (1,8,0,next_read_bits_states)
        else:
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (1,8,0,next_read_bits_states_le)
    elif (options.unread_bit):
        if (not options.little_endian):
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (0,8,0,next_unread_bit_states)
        else:
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (0,8,0,next_unread_bit_states_le)
    elif (options.read_unary):
        if (not options.little_endian):
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (1,8,0,next_read_unary_states)
        else:
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (1,8,0,next_read_unary_states_le)
    elif (options.read_limited_unary):
        if (not options.little_endian):
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (1,8,0,next_read_limited_unary_states)
        else:
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (1,8,0,next_read_limited_unary_states_le)
    elif (options.write_bits):
        if (not options.little_endian):
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (0,7,0,next_write_bits_states)
        else:
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (0,7,0,next_write_bits_states_le)
    elif (options.write_unary):
        if (not options.little_endian):
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (0,7,0,next_write_unary_states)
        else:
            (minimum_bits,maximum_bits,start_context,stat_function) = \
                (0,7,0,next_write_unary_states_le)
    else:
        sys.exit(0)

    state_map = dict([(context,list(stat_function(context)))
                      for context in states(minimum_bits=minimum_bits,
                                            maximum_bits=maximum_bits)])

    map_width = max(map(len,state_map.values()))

    sys.stdout.write("{\n")
    for (last,i) in last_element(range(start_context,
                                       max(state_map.keys()) + 1)):
        sys.stdout.write("/* 0x%X */\n" % (i))
        if (i in state_map):
            sys.stdout.write(int_row(state_map[i],last))
        else:
            sys.stdout.write(int_row([0] * map_width,last))
    sys.stdout.write("}\n")
