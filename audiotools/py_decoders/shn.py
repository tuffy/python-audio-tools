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
from audiotools import parse_fmt,parse_comm
import cStringIO

def shnmean(values):
    return ((len(values) / 2) + sum(values)) / len(values)


class SHNDecoder:
    def __init__(self, filename):
        self.reader = BitstreamReader(open(filename, "rb"), 0)

        (self.file_type,
         self.channels,
         self.block_length,
         self.max_LPC,
         self.number_of_means) = self.read_header()

        if ((1 <= self.file_type) and (self.file_type <= 2)):
            self.bits_per_sample = 8
            self.signed_samples = (self.file_type == 1)
        elif ((3 <= self.file_type) and (self.file_type <= 6)):
            self.bits_per_sample = 16
            self.signed_samples = (self.file_type in (3, 5))
        else:
            raise ValueError("unsupported Shorten file type")

        self.wrapped_samples = [[0] * 3 for c in xrange(self.channels)]
        self.means = [[0] * self.number_of_means for c in xrange(self.channels)]
        self.left_shift = 0
        self.stream_finished = False

        #try to read the first command for a wave/aiff header
        self.reader.mark()
        self.read_metadata()
        self.reader.rewind()
        self.reader.unmark()

    def read_metadata(self):
        command = self.unsigned(2)
        if (command == 9):
            #got verbatim, so read data
            verbatim_bytes = "".join([chr(self.unsigned(8) & 0xFF)
                                      for i in xrange(self.unsigned(5))])

            try:
                wave = BitstreamReader(cStringIO.StringIO(verbatim_bytes), 1)
                header = wave.read_bytes(12)
                if (header.startswith("RIFF") and header.endswith("WAVE")):
                    #got RIFF/WAVE header, so parse wave blocks as needed
                    total_size = len(verbatim_bytes) - 12
                    while (total_size > 0):
                        (chunk_id, chunk_size) = wave.parse("4b 32u")
                        total_size -= 8
                        if (chunk_id == 'fmt '):
                            (channels,
                             self.sample_rate,
                             bits_per_sample,
                             channel_mask) = parse_fmt(
                                wave.substream(chunk_size))
                            self.channel_mask = int(channel_mask)
                            return
                        else:
                            if (chunk_size % 2):
                                wave.read_bytes(chunk_size + 1)
                                total_size -= (chunk_size + 1)
                            else:
                                wave.read_bytes(chunk_size)
                                total_size -= chunk_size
                    else:
                        #no fmt chunk, so use default metadata
                        pass
            except (IOError,ValueError):
                pass

            try:
                aiff = BitstreamReader(cStringIO.StringIO(verbatim_bytes), 0)
                header = aiff.read_bytes(12)
                if (header.startswith("FORM") and header.endswith("AIFF")):
                    #got FORM/AIFF header, so parse aiff blocks as needed
                    total_size = len(verbatim_bytes) - 12
                    while (total_size > 0):
                        (chunk_id, chunk_size) = aiff.parse("4b 32u")
                        total_size -= 8
                        if (chunk_id == 'COMM'):
                            (channels,
                             total_sample_frames,
                             bits_per_sample,
                             self.sample_rate,
                             channel_mask) = parse_comm(
                                aiff.substream(chunk_size))
                            self.channel_mask = int(channel_mask)
                            return
                        else:
                            if (chunk_size % 2):
                                aiff.read_bytes(chunk_size + 1)
                                total_size -= (chunk_size + 1)
                            else:
                                aiff.read_bytes(chunk_size)
                                total_size -= chunk_size
                    else:
                        #no COMM chunk, so use default metadata
                        pass
            except IOError:
                pass

        #got something else, so invent some PCM parameters
        self.sample_rate = 44100
        if (self.channels == 1):
            self.channel_mask = 0x4
        elif (self.channels == 2):
            self.channel_mask = 0x3
        else:
            self.channel_mask = 0

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
            return from_channels([from_list([], 1,
                                            self.bits_per_sample,
                                            self.signed_samples)
                                  for channel in xrange(self.channels)])

        c = 0
        samples = []
        unshifted = []
        while (True):
            command = self.unsigned(2)
            print "command : %s" % (command)
            if ((0 <= command) and (command <= 3) or
                (7 <= command) and (command <= 8)):
                #audio data commands
                if (command == 0):   #DIFF0
                    samples.append(self.read_diff0(self.block_length,
                                                   self.means[c]))
                elif (command == 1): #DIFF1
                    samples.append(self.read_diff1(self.block_length,
                                                   self.wrapped_samples[c]))
                elif (command == 2): #DIFF2
                    samples.append(self.read_diff2(self.block_length,
                                                   self.wrapped_samples[c]))
                elif (command == 3): #DIFF3
                    samples.append(self.read_diff3(self.block_length,
                                                   self.wrapped_samples[c]))
                elif (command == 7): #QLPC
                    samples.append(self.read_qlpc(self.block_length,
                                                  self.means[c],
                                                  self.wrapped_samples[c]))
                elif (command == 8): #ZERO
                    samples.append([0] * self.block_length)

                #update means for channel
                self.means[c].append(shnmean(samples[c]))
                self.means[c] = self.means[c][1:]

                #wrap samples for next command in channel
                self.wrapped_samples[c] = samples[c][-(max(3, self.max_LPC)):]

                #apply left shift to samples
                if (self.left_shift > 0):
                    unshifted.append([s << self.left_shift for s in samples[c]])
                else:
                    unshifted.append(samples[c])

                c += 1
                if (c == self.channels):
                    #return a FrameList from shifted data
                    return from_channels([from_list(channel, 1,
                                                    self.bits_per_sample,
                                                    self.signed_samples)
                                          for channel in unshifted])
            else:
                #non audio commands
                if (command == 4): #QUIT
                    self.stream_finished = True
                    return from_channels([from_list([], 1,
                                                    self.bits_per_sample,
                                                    self.signed_samples)
                                          for channel in xrange(self.channels)])
                elif (command == 5): #BLOCKSIZE
                    self.block_length = self.long()
                elif (command == 6): #BITSHIFT
                    self.left_shift = self.unsigned(2)
                elif (command == 9): #VERBATIM
                    #skip this command during reading
                    size = self.unsigned(5)
                    for i in xrange(size):
                        self.skip_unsigned(8)
                else:
                    raise ValueError("unsupported Shorten command")

    def read_diff0(self, block_length, means):
        offset = shnmean(means)
        energy = self.unsigned(3)
        samples = []
        for i in xrange(block_length):
            residual = self.signed(energy)
            samples.append(residual + offset)
        return samples

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

    def read_qlpc(self, block_length, means, previous_samples):
        offset = shnmean(means)
        energy = self.unsigned(3)
        LPC_count = self.unsigned(2)
        LPC_coeff = [self.signed(5) for i in xrange(LPC_count)]
        unoffset = []
        samples = previous_samples[-LPC_count:]
        for i in xrange(block_length):
            residual = self.signed(energy)
            LPC_sum = 2 ** 5
            for j in xrange(LPC_count):
                if ((i - j - 1) < 0):
                    #apply offset to warm-up samples
                    LPC_sum += (LPC_coeff[j] *
                                (samples[LPC_count + (i - j - 1)] - offset))
                else:
                    LPC_sum += LPC_coeff[j] * unoffset[i - j - 1]
            unoffset.append(LPC_sum / 2 ** 5 + residual)
        return [u + offset for u in unoffset]

    def close(self):
        self.reader.close()
