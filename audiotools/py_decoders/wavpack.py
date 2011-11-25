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

from audiotools.bitstream import BitstreamReader
from math import log

class WavPackDecoder:
    def __init__(self, filename):
        self.reader = BitstreamReader(open(filename, "rb"), 1)
        self.pcm_finished = False
        self.md5_checked = False

    def read(self):
        while (True):  #in place of a do-while loop
            self.reset_decoding_parameters()
            header = Block_Header.read(self.reader)
            sub_blocks_size = header.block_size - 24
            sub_blocks_data = self.reader.substream(sub_blocks_size)
            while (sub_blocks_size > 0):
                sub_block = Sub_Block.read(sub_blocks_data)
                if (sub_block.nondecoder_data == 0):
                    if (sub_block.metadata_function == 2):
                        self.parse_decorrelation_terms(sub_block)
                    elif (sub_block.metadata_function == 3):
                        self.parse_decorrelation_weights(header, sub_block)
                    elif (sub_block.metadata_function == 4):
                        self.parse_decorrelation_samples(header, sub_block)
                    elif (sub_block.metadata_function == 5):
                        self.parse_entropy_variables(header, sub_block)
                    elif (sub_block.metadata_function == 10):
                        self.parse_bitstream(header, sub_block)
                    else:
                        #FIXME - parse decoding parameters from sub block
                        pass
                sub_blocks_size -= sub_block.total_size()

            #FIXME - decode to 1 or 2 channels of audio data

            if (header.final_block == 1):
                break

        #FIXME - combine channels of audio data into single block

        #FIXME - update MD5 sum

        #FIXME - return single block of audio data
        return None

    def close(self):
        self.reader.close()

    def reset_decoding_parameters(self):
        self.decorrelation_terms = []
        self.decorrelation_deltas = []
        self.channel_A_weights = []
        self.channel_B_weights = []
        self.medians = []

        self.decorrelation_terms_read = False
        self.decorrelation_weights_read = False
        self.entropy_variables_read = False

    def parse_decorrelation_terms(self, sub_block):
        if (sub_block.actual_size_1_less == 0):
            passes = sub_block.sub_block_size * 2
        else:
            passes = sub_block.sub_block_size * 2 - 1

        if (passes > 16):
            raise ValueError("invalid decorrelation passes count")

        self.decorrelation_terms = []
        self.decorrelation_deltas = []
        for i in xrange(passes):
            self.decorrelation_terms.append(sub_block.data.read(5) - 5)
            if (not (((1 <= self.decorrelation_terms[-1]) and
                      (self.decorrelation_terms[-1] <= 18)) or
                     ((-3 <= self.decorrelation_terms[-1]) and
                      (self.decorrelation_terms[-1] <= -1)))):
                raise ValueError("invalid decorrelation term")
            self.decorrelation_deltas.append(sub_block.data.read(3))

        self.decorrelation_terms.reverse()
        self.decorrelation_deltas.reverse()

        self.decorrelation_terms_read = True

    def parse_decorrelation_weights(self, block_header, sub_block):
        assert(self.decorrelation_terms_read)

        if (sub_block.actual_size_1_less == 0):
            weight_count = sub_block.sub_block_size * 2
        else:
            weight_count = sub_block.sub_block_size * 2 - 1

        weights = []
        for i in xrange(weight_count):
            value_i = sub_block.data.read_signed(8)
            if (value_i > 0):
                weights.append((value_i * 2 ** 3) +
                               ((value_i * 2 ** 3 + 2 ** 6) / 2 ** 7))
            elif(value_i == 0):
                weights.append(0)
            else:
                weights.append(value_i * 2 ** 3)

        self.channel_A_weights = []
        self.channel_B_weights = []
        if (block_header.mono_output == 0):
            if ((weight_count / 2) > len(self.decorrelation_terms)):
                raise ValueError("invalid number of decorrelation weights")
            for i in xrange(weight_count / 2):
                self.channel_A_weights.append(weights[i * 2])
                self.channel_B_weights.append(weights[i * 2 + 1])
            for i in xrange(weight_count / 2, len(self.decorrelation_terms)):
                self.channel_A_weights.append(0)
                self.channel_B_weights.append(0)
            self.channel_A_weights.reverse()
            self.channel_B_weights.reverse()
        else:
            if (weight_count > len(self.decorrelation_terms)):
                raise ValueError("invalid number of decorrelation weights")
            for i in xrange(weight_count):
                self.channel_A_weights.append(weights[i])
            for i in xrange(weight_count, len(self.decorrelation_terms)):
                self.channel_B_weights.append(0)
            self.channel_A_weights.reverse()

        self.decorrelation_weights_read = True

    def parse_decorrelation_samples(self, header, sub_block):
        assert(self.decorrelation_terms_read)
        sub_block_bytes = sub_block.data_size()

        channel_A_samples = []
        channel_B_samples = []
        if (header.mono_output == 0):
            for term in reversed(self.decorrelation_terms):
                if ((17 <= term) and (term <= 18)):
                    if (sub_block_bytes >= 8):
                        channel_A_samples.append([read_exp2(sub_block.data),
                                                  read_exp2(sub_block.data)])
                        channel_B_samples.append([read_exp2(sub_block.data),
                                                  read_exp2(sub_block.data)])
                        sub_block_bytes -= 8
                    else:
                        channel_A_samples.append([0, 0])
                        channel_B_samples.append([0, 0])
                        sub_block_bytes = 0
                elif ((1 <= term) and (term <= 8)):
                    if (sub_block_bytes >= (term * 4)):
                        channel_A_samples.append([read_exp2(sub_block.data)
                                                  for i in xrange(term)])
                        channel_B_samples.append([read_exp2(sub_block.data)
                                                  for i in xrange(term)])
                        sub_block_bytes -= (term * 4)
                    else:
                        channel_A_samples.append([0 for i in xrange(term)])
                        channel_B_samples.append([0 for i in xrange(term)])
                        sub_block_bytes = 0
                elif ((-3 <= term) and (term <= -1)):
                    if (sub_block_bytes >= 4):
                        channel_A_samples.append([read_exp2(sub_block.data)])
                        channel_B_samples.append([read_exp2(sub_block.data)])
                        sub_block_bytes -= 4
                    else:
                        channel_A_samples.append([0])
                        channel_B_samples.append([0])
                        sub_block_bytes = 0
                else:
                    raise ValueError("invalid decorrelation term")
        else:
            for term in reversed(self.decorrelation_terms):
                if ((17 <= term) and (term <= 18)):
                    if (sub_block_bytes >= 4):
                        channel_A_samples.append([read_exp2(sub_block.data),
                                                  read_exp2(sub_block.data)])
                        sub_block_bytes -= 4
                    else:
                        channel_A_samples.append([0, 0])
                        sub_block_bytes = 0
                elif ((1 <= term) and (term <= 8)):
                    if (sub_block_bytes >= (term * 2)):
                        channel_A_samples.append([read_exp2(sub_block.data)
                                                  for i in xrange(term)])
                        sub_block_bytes -= (term * 2)
                    else:
                        channel_A_samples.append([0 for i in xrange(term)])
                        sub_block_bytes = 0
                else:
                    raise ValueError("invalid decorrelation term")

        channel_A_samples.reverse()
        channel_B_samples.reverse()

        return (channel_A_samples, channel_B_samples)

    def parse_entropy_variables(self, header, sub_block):
        median0 = [read_exp2(sub_block.data) for i in xrange(3)]
        if (header.mono_output == 0):
            median1 = [read_exp2(sub_block.data) for i in xrange(3)]
        else:
            median1 = [0 for i in xrange(3)]

        self.entropy_variables_read = True
        self.medians = (median0, median1)

    def parse_bitstream(self, header, sub_block):
        assert(self.entropy_variables_read)

        if (header.mono_output):
            channel_count = 1
            residuals = [[]]
        else:
            channel_count = 2
            residuals = [[],[]]

        holding_zero = 0
        holding_one = 0
        i = 0
        while (i < (header.block_samples * channel_count)):
            if ((holding_zero == 0) and (holding_one == 0) and
                (self.medians[0][0] < 2) and (self.medians[1][0] < 2)):
                #handle long run of 0 residuals
                t = sub_block.data.unary(0)
                if (t > 1):
                    p = sub_block.data.read(t - 1)
                    zeroes = (2 ** (t - 1)) + p
                else:
                    zeroes = t
                if (zeroes > 0):
                    for j in xrange(zeroes):
                        residuals[i % channel_count].append(0)
                        i += 1
                    self.medians = ([0, 0, 0], [0, 0, 0])
                if (i < (header.block_samples * channel_count)):
                    (residual,
                     holding_zero,
                     holding_one) = self.read_residual(
                        sub_block.data,
                        holding_zero,
                        holding_one,
                        self.medians[i % channel_count])
                    residuals[i % channel_count].append(residual)
                    i += 1
            else:
                (residual,
                 holding_zero,
                 holding_one) = self.read_residual(
                    sub_block.data,
                    holding_zero,
                    holding_one,
                    self.medians[i % channel_count])
                residuals[i % channel_count].append(residual)
                i += 1

    def read_residual(self, reader, holding_zero, holding_one, medians):
        if (holding_zero == 0):
            t = reader.unary(0)
            if (t == 16):
                u = reader.unary(0)
                if (u > 1):
                    e = reader.read(u - 1)
                    t += 2 ** (u - 1) + e
                else:
                    t += u

            if (holding_one == 0):
                holding_one = t % 2
                holding_zero = 1 - holding_one
                t = t >> 1
            else:
                holding_one = t % 2
                holding_zero = 1 - holding_one
                t = (t >> 1) + 1
        else:
            t = 0
            holding_zero = 0

        if (t == 0):
            base = 0
            add = medians[0] >> 4
            medians[0] -= ((medians[0] + 126) >> 7) * 2
        elif (t == 1):
            base = (medians[0] >> 4) + 1
            add = medians[1] >> 4
            medians[0] += ((medians[0] + 128) >> 7) * 5
            medians[1] -= ((medians[1] + 62) >> 6) * 2
        elif (t == 2):
            base = ((medians[0] >> 4) + 1) + ((medians[1] >> 4) + 1)
            add = medians[2] >> 4
            medians[0] += ((medians[0] + 128) >> 7) * 5
            medians[1] += ((medians[1] + 64) >> 6) * 5
            medians[2] -= ((medians[2] + 30) >> 5) * 2
        else:
            base = (((medians[0] >> 4) + 1) +
                    ((medians[1] >> 4) + 1) +
                    (((medians[2] >> 4) + 1) * (t - 2)))
            add = medians[2] >> 4
            medians[0] += ((medians[0] + 128) >> 7) * 5
            medians[1] += ((medians[1] + 64) >> 6) * 5
            medians[2] += ((medians[2] + 32) >> 5) * 5

        if (add >= 1):
            p = int(log(add) / log(2))
            if (p > 0):
                r = reader.read(p)
            else:
                r = 0

            e = (1 << (p + 1)) - add - 1

            if (r >= e):
                b = reader.read(1)
                unsigned = base + (r * 2) - e + b
            else:
                unsigned = base + r
        else:
            unsigned = base

        sign = reader.read(1)
        if (sign == 1):
            return (-unsigned - 1, holding_zero, holding_one)
        else:
            return (unsigned, holding_zero, holding_one)



EXP2 = [0x100, 0x101, 0x101, 0x102, 0x103, 0x103, 0x104, 0x105,
        0x106, 0x106, 0x107, 0x108, 0x108, 0x109, 0x10a, 0x10b,
        0x10b, 0x10c, 0x10d, 0x10e, 0x10e, 0x10f, 0x110, 0x110,
        0x111, 0x112, 0x113, 0x113, 0x114, 0x115, 0x116, 0x116,
        0x117, 0x118, 0x119, 0x119, 0x11a, 0x11b, 0x11c, 0x11d,
        0x11d, 0x11e, 0x11f, 0x120, 0x120, 0x121, 0x122, 0x123,
        0x124, 0x124, 0x125, 0x126, 0x127, 0x128, 0x128, 0x129,
        0x12a, 0x12b, 0x12c, 0x12c, 0x12d, 0x12e, 0x12f, 0x130,
        0x130, 0x131, 0x132, 0x133, 0x134, 0x135, 0x135, 0x136,
        0x137, 0x138, 0x139, 0x13a, 0x13a, 0x13b, 0x13c, 0x13d,
        0x13e, 0x13f, 0x140, 0x141, 0x141, 0x142, 0x143, 0x144,
        0x145, 0x146, 0x147, 0x148, 0x148, 0x149, 0x14a, 0x14b,
        0x14c, 0x14d, 0x14e, 0x14f, 0x150, 0x151, 0x151, 0x152,
        0x153, 0x154, 0x155, 0x156, 0x157, 0x158, 0x159, 0x15a,
        0x15b, 0x15c, 0x15d, 0x15e, 0x15e, 0x15f, 0x160, 0x161,
        0x162, 0x163, 0x164, 0x165, 0x166, 0x167, 0x168, 0x169,
        0x16a, 0x16b, 0x16c, 0x16d, 0x16e, 0x16f, 0x170, 0x171,
        0x172, 0x173, 0x174, 0x175, 0x176, 0x177, 0x178, 0x179,
        0x17a, 0x17b, 0x17c, 0x17d, 0x17e, 0x17f, 0x180, 0x181,
        0x182, 0x183, 0x184, 0x185, 0x187, 0x188, 0x189, 0x18a,
        0x18b, 0x18c, 0x18d, 0x18e, 0x18f, 0x190, 0x191, 0x192,
        0x193, 0x195, 0x196, 0x197, 0x198, 0x199, 0x19a, 0x19b,
        0x19c, 0x19d, 0x19f, 0x1a0, 0x1a1, 0x1a2, 0x1a3, 0x1a4,
        0x1a5, 0x1a6, 0x1a8, 0x1a9, 0x1aa, 0x1ab, 0x1ac, 0x1ad,
        0x1af, 0x1b0, 0x1b1, 0x1b2, 0x1b3, 0x1b4, 0x1b6, 0x1b7,
        0x1b8, 0x1b9, 0x1ba, 0x1bc, 0x1bd, 0x1be, 0x1bf, 0x1c0,
        0x1c2, 0x1c3, 0x1c4, 0x1c5, 0x1c6, 0x1c8, 0x1c9, 0x1ca,
        0x1cb, 0x1cd, 0x1ce, 0x1cf, 0x1d0, 0x1d2, 0x1d3, 0x1d4,
        0x1d6, 0x1d7, 0x1d8, 0x1d9, 0x1db, 0x1dc, 0x1dd, 0x1de,
        0x1e0, 0x1e1, 0x1e2, 0x1e4, 0x1e5, 0x1e6, 0x1e8, 0x1e9,
        0x1ea, 0x1ec, 0x1ed, 0x1ee, 0x1f0, 0x1f1, 0x1f2, 0x1f4,
        0x1f5, 0x1f6, 0x1f8, 0x1f9, 0x1fa, 0x1fc, 0x1fd, 0x1ff]

def read_exp2(reader):
    value = reader.read_signed(16)
    if ((-32768 <= value) and (value < -2304)):
        return -(EXP2[-value & 0xFF] << ((-value >> 8) - 9))
    elif ((-2304 <= value) and (value < 0)):
        return -(EXP2[-value & 0xFF] >> (9 - (-value >> 8)))
    elif ((0 <= value) and (value <= 2304)):
        return EXP2[value & 0xFF] >> (9 - (value >> 8))
    elif ((2304 < value) and (value <= 32767)):
        return EXP2[value & 0xFF] << ((value >> 8) - 9)


class Block_Header:
    def __init__(self,
                 block_id, block_size, version, track_number, index_number,
                 total_samples, block_index, block_samples, bits_per_sample,
                 mono_output, hybrid_mode, joint_stereo, channel_decorrelation,
                 hybrid_noise_shaping, floating_point_data,
                 extended_size_integers, hybrid_controls_bitrate,
                 hybrid_noise_balanced, initial_block, final_block,
                 left_shift_data, maximum_magnitude, sample_rate,
                 use_IIR, false_stereo, CRC):
        if (block_id != "wvpk"):
            raise ValueError("invalid WavPack block ID")
        self.block_size = block_size
        self.version = version
        self.track_number = track_number
        self.index_number = index_number
        self.total_samples = total_samples
        self.block_index = block_index
        self.block_samples = block_samples
        self.bits_per_sample = bits_per_sample
        self.mono_output = mono_output
        self.hybrid_mode = hybrid_mode
        self.joint_stereo = joint_stereo
        self.channel_decorrelation = channel_decorrelation
        self.hybrid_noise_shaping = hybrid_noise_shaping
        self.floating_point_data = floating_point_data
        self.extended_size_integers = extended_size_integers
        self.hybrid_controls_bitrate = hybrid_controls_bitrate
        self.hybrid_noise_balanced = hybrid_noise_balanced
        self.initial_block = initial_block
        self.final_block = final_block
        self.left_shift_data = left_shift_data
        self.maximum_magnitude = maximum_magnitude
        self.sample_rate = sample_rate
        self.use_IIR = use_IIR
        self.false_stereo = false_stereo
        self.CRC = CRC

    def __repr__(self):
        return "Block_Header(%s)" % \
            ", ".join(["%s=%s" % (attr, getattr(self, attr))
                       for attr in
                       ["block_size", "version", "track_number",
                        "index_number", "total_samples", "block_index",
                        "block_samples", "bits_per_sample", "mono_output",
                        "hybrid_mode", "joint_stereo",
                        "channel_decorrelation", "hybrid_noise_shaping",
                        "floating_point_data", "extended_size_integers",
                        "hybrid_controls_bitrate", "hybrid_noise_balanced",
                        "initial_block", "final_block", "left_shift_data",
                        "maximum_magnitude", "sample_rate",
                        "use_IIR", "false_stereo", "CRC"]])

    @classmethod
    def read(cls, reader):
        return cls(*reader.parse(
                "4b 32u 16u 8u 8u 32u 32u 32u" +
                "2u 1u 1u 1u 1u 1u 1u 1u " +
                "1u 1u 1u 1u 5u 5u 4u 2p 1u 1u 1p" +
                "32u"))

class Sub_Block:
    def __init__(self, metadata_function, nondecoder_data,
                 actual_size_1_less, large_block, sub_block_size,
                 data):
        self.metadata_function = metadata_function
        self.nondecoder_data = nondecoder_data
        self.actual_size_1_less = actual_size_1_less
        self.large_block = large_block
        self.sub_block_size = sub_block_size
        self.data = data

    def __repr__(self):
        return "Sub_Block(%s)" % \
            ", ".join(["%s=%s" % (attr, getattr(self, attr))
                       for attr in
                       ["metadata_function", "nondecoder_data",
                        "actual_size_1_less", "large_block",
                        "sub_block_size", "data"]])

    def total_size(self):
        if (self.large_block):
            return 1 + 3 + (self.sub_block_size * 2)
        else:
            return 1 + 1 + (self.sub_block_size * 2)

    def data_size(self):
        if (self.actual_size_1_less):
            return self.sub_block_size * 2 - 1
        else:
            return self.sub_block_size * 2

    @classmethod
    def read(cls, reader):
        (metadata_function,
         nondecoder_data,
         actual_size_1_less,
         large_block) = reader.parse("5u 1u 1u 1u")

        if (large_block == 0):
            sub_block_size = reader.read(8)
        else:
            sub_block_size = reader.read(24)

        if (actual_size_1_less == 0):
            data = reader.substream(sub_block_size * 2)
        else:
            data = reader.substream(sub_block_size * 2 - 1)
            reader.skip(8)

        return cls(metadata_function,
                   nondecoder_data,
                   actual_size_1_less,
                   large_block,
                   sub_block_size,
                   data)
