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

from audiotools.bitstream import BitstreamReader
from audiotools.pcm import from_list,from_channels

class SHNDecoder:
    def __init__(self, filename):
        self.reader = BitstreamReader(open(filename, "rb"), 0)

        (self.file_type,
         self.channels,
         self.block_length,
         self.max_LPC,
         self.number_of_means) = self.read_header()

        self.offsets = 0
        self.left_shift = 0
        self.wrapped_samples = [[0] * 3 for c in xrange(self.channels)]
        self.stream_finished = False

        #FIXME - determine sample rate from Wave/AIFF header

    def unsigned(self, c):
        MSB = self.reader.unary(1)
        LSB = self.reader.read(c)
        return MSB * 2 ** c + LSB

    def signed(self, c):
        u = self.unsigned(c + 1)
        if ((u % 2) == 0):
            return u / 2
        else:
            return -(u / 2) - 1

    def long(self):
        return self.unsigned(self.unsigned(2))

    def skip_unsigned(self, c):
        self.reader.skip_unary(1)
        self.reader.skip(c)

    def read_header(self):
        magic = self.reader.read_bytes(4)
        if (magic != "ajkg"):
            raise ValueError("invalid magic number")
        version = self.reader.read(8)
        if (version != 2):
            raise ValueError("unsupported version")

        file_type = self.long()
        channels = self.long()
        block_length = self.long()
        max_LPC = self.long()
        number_of_means = self.long()
        bytes_to_skip = self.long()
        self.reader.read_bytes(bytes_to_skip)

        return (file_type, channels, block_length, max_LPC, number_of_means)

    def read(self, bytes):
        if (self.stream_finished):
            #FIXME - make bits-per-sample and sign dynamic
            return from_channels([from_list([], 1, 16, True)
                                  for channel in xrange(self.channels)])

        c = 0
        samples = []
        while (c < self.channels):
            command = self.unsigned(2)
            if (command == 0):   #DIFF0
                raise NotImplementedError()
            elif (command == 1): #DIFF1
                samples.append(self.read_diff1(self.block_length,
                                               self.wrapped_samples[c]))
                c += 1
            elif (command == 2): #DIFF2
                samples.append(self.read_diff2(self.block_length,
                                               self.wrapped_samples[c]))
                c += 1
            elif (command == 3): #DIFF3
                samples.append(self.read_diff3(self.block_length,
                                               self.wrapped_samples[c]))
                c += 1
            elif (command == 4): #QUIT
                self.stream_finished = True
                #FIXME - make bits-per-sample and sign dynamic
                return from_channels([from_list([], 1, 16, True)
                                      for channel in xrange(self.channels)])
            elif (command == 5): #BLOCKSIZE
                self.block_length = self.long()
            elif (command == 6): #BITSHIFT
                raise NotImplementedError()
            elif (command == 7): #QLPC
                raise NotImplementedError()
            elif (command == 8): #ZERO
                raise NotImplementedError()
            elif (command == 9): #VERBATIM
                #skip this command during reading
                size = self.unsigned(5)
                for i in xrange(size):
                    self.skip_unsigned(8)
            else:
                raise ValueError("unsupported Shorten command")

        #all channels have been read
        #so wrap trailing samples for the next set of channels
        self.wrapped_samples = [channel[-3:] for channel in samples]

        #apply any left shift
        if (self.left_shift > 0):
            raise NotImplementedError()

        #and return a FrameList
        #FIXME - make bits-per-sample and sign dynamic
        return from_channels([from_list(channel, 1, 16, True)
                              for channel in samples])

    def read_diff1(self, block_length, previous_samples):
        samples = previous_samples[-1:]
        energy = self.unsigned(3)
        for i in xrange(1, block_length + 1):
            residual = self.signed(energy)
            samples.append(samples[i - 1] + residual)
        return samples[1:]

    def read_diff2(self, block_length, previous_samples):
        samples = previous_samples[-2:]
        energy = self.unsigned(3)
        for i in xrange(2, block_length + 2):
            residual = self.signed(energy)
            samples.append((2 * samples[i - 1]) - samples[i - 2] + residual)
        return samples[2:]

    def read_diff3(self, block_length, previous_samples):
        samples = previous_samples[-3:]
        energy = self.unsigned(3)
        for i in xrange(3, block_length + 3):
            residual = self.signed(energy)
            samples.append((3 * (samples[i - 1] - samples[i - 2])) +
                           samples[i - 3] + residual)
        return samples[3:]

    def close(self):
        self.reader.close()
