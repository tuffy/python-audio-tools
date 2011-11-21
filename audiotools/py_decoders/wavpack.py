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
                    else:
                        #FIXME - parser decoding parameters from sub block
                        print sub_block.metadata_function
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

    def parse_decorrelation_weights(self, block_header, sub_block):
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

        print repr(self.channel_A_weights),repr(self.channel_B_weights)

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
                        "large_block", "sub_block_data", "data"]])

    def total_size(self):
        if (self.large_block):
            return 1 + 3 + (self.sub_block_size * 2)
        else:
            return 1 + 1 + (self.sub_block_size * 2)

    def data_size(self):
        if (self.actual_size_1_less):
            return self.sub_block_size * 2 - 1
        else:
            return self.sub_block_size * 2 - 1

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
