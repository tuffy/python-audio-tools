#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2014  Brian Langenberger

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
from audiotools.pcm import from_channels, from_list
from math import log
from hashlib import md5


def sub_blocks(reader, sub_blocks_size):
    while (sub_blocks_size > 0):
        sub_block = Sub_Block.read(reader)
        yield sub_block
        sub_blocks_size -= sub_block.total_size()


class WavPackDecoder:
    def __init__(self, filename):
        self.reader = BitstreamReader(open(filename, "rb"), 1)

        #read initial block to populate
        #sample_rate, bits_per_sample, channels, and channel_mask
        self.reader.mark()
        block_header = Block_Header.read(self.reader)
        sub_blocks_size = block_header.block_size - 24
        sub_blocks_data = self.reader.substream(sub_blocks_size)
        if (block_header.sample_rate != 15):
            self.sample_rate = [6000,  8000,  9600,  11025, 12000,
                                16000, 22050, 24000, 32000, 44100,
                                48000, 64000, 88200, 96000,
                                192000][block_header.sample_rate]
        else:
            sub_blocks_data.mark()
            try:
                for sub_block in sub_blocks(sub_blocks_data, sub_blocks_size):
                    if (((sub_block.metadata_function == 7) and
                         (sub_block.nondecoder_data == 1))):
                        self.sample_rate = sub_block.data.read(
                            sub_block.data_size() * 8)
                        break
                else:
                    raise ValueError("invalid sample rate")
            finally:
                sub_blocks_data.rewind()
                sub_blocks_data.unmark()

        self.bits_per_sample = [8, 16, 24, 32][block_header.bits_per_sample]

        if (block_header.initial_block and block_header.final_block):
            if (((block_header.mono_output == 0) or
                 (block_header.false_stereo == 1))):
                self.channels = 2
                self.channel_mask = 0x3
            else:
                self.channels = 1
                self.channel_mask = 0x4
        else:
            #look for channel mask sub block
            sub_blocks_data.mark()
            for sub_block in sub_blocks(sub_blocks_data, sub_blocks_size):
                if (((sub_block.metadata_function == 13) and
                     (sub_block.nondecoder_data == 0))):
                    self.channels = sub_block.data.read(8)
                    self.channel_mask = sub_block.data.read(
                        (sub_block.data_size() - 1) * 8)
                    break
            else:
                #FIXME - handle case of no channel mask sub block
                raise NotImplementedError()
            sub_blocks_data.rewind()
            sub_blocks_data.unmark()

        self.reader.rewind()
        self.reader.unmark()

        self.pcm_finished = False
        self.md5_checked = False
        self.md5sum = md5()

    def read(self, pcm_frames):
        if (self.pcm_finished):
            if (not self.md5_checked):
                self.reader.mark()
                try:
                    try:
                        header = Block_Header.read(self.reader)
                        sub_blocks_size = header.block_size - 24
                        sub_blocks_data = \
                            self.reader.substream(sub_blocks_size)
                        for sub_block in sub_blocks(sub_blocks_data,
                                                    sub_blocks_size):
                            if (((sub_block.metadata_function == 6) and
                                 (sub_block.nondecoder_data == 1))):
                                if ((sub_block.data.read_bytes(16) !=
                                     self.md5sum.digest())):
                                    raise ValueError("invalid stream MD5 sum")
                    except (IOError, ValueError):
                        #no error if a block isn't found
                        pass
                finally:
                    self.reader.rewind()
                    self.reader.unmark()
            return from_list([], self.channels, self.bits_per_sample, True)

        channels = []

        while (True):  # in place of a do-while loop
            try:
                block_header = Block_Header.read(self.reader)
            except (ValueError, IOError):
                self.pcm_finished = True
                return from_list([], self.channels, self.bits_per_sample, True)
            sub_blocks_size = block_header.block_size - 24
            sub_blocks_data = self.reader.substream(sub_blocks_size)
            channels.extend(read_block(block_header,
                                       sub_blocks_size,
                                       sub_blocks_data))

            if (block_header.final_block == 1):
                break

        if ((block_header.block_index +
             block_header.block_samples) >= block_header.total_samples):
            self.pcm_finished = True

        #combine channels of audio data into single block
        block = from_channels([from_list(ch, 1, self.bits_per_sample, True)
                               for ch in channels])

        #update MD5 sum
        self.md5sum.update(block.to_bytes(False, self.bits_per_sample > 8))

        #return single block of audio data
        return block

    def close(self):
        self.reader.close()


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
        return cls(*reader.parse("4b 32u 16u 8u 8u 32u 32u 32u" +
                                 "2u 11* 1u 5u 5u 4u 2p 1u 1u 1p" +
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


def read_block(block_header, sub_blocks_size, sub_blocks_data):
    """returns 1 or 2 channels of PCM data integers"""

    decorrelation_terms_read = False
    decorrelation_weights_read = False
    decorrelation_samples_read = False
    entropies_read = False
    residuals_read = False
    extended_integers_read = False

    while (sub_blocks_size > 0):
        (metadata_function,
         nondecoder_data,
         actual_size_1_less,
         large_sub_block) = sub_blocks_data.parse("5u 1u 1u 1u")
        if (large_sub_block == 0):
            sub_block_size = sub_blocks_data.read(8)
        else:
            sub_block_size = sub_blocks_data.read(24)
        if (actual_size_1_less == 0):
            sub_block_data = sub_blocks_data.substream(sub_block_size * 2)
        else:
            sub_block_data = sub_blocks_data.substream(sub_block_size * 2 - 1)
            sub_blocks_data.skip(8)

        if (nondecoder_data == 0):
            if (metadata_function == 2):
                (decorrelation_terms,
                 decorrelation_deltas) = read_decorrelation_terms(
                    sub_block_size, actual_size_1_less, sub_block_data)
                decorrelation_terms_read = True
            if (metadata_function == 3):
                if (not decorrelation_terms_read):
                    raise ValueError(
                        "weights sub block found before terms sub block")
                decorrelation_weights = read_decorrelation_weights(
                    block_header, len(decorrelation_terms),
                    sub_block_size, actual_size_1_less, sub_block_data)
                decorrelation_weights_read = True
            if (metadata_function == 4):
                if (not decorrelation_terms_read):
                    raise ValueError(
                        "samples sub block found before terms sub block")
                if (actual_size_1_less):
                    raise ValueError(
                        "decorrelation samples must have an even byte count")
                decorrelation_samples = read_decorrelation_samples(
                    block_header, decorrelation_terms,
                    sub_block_size, sub_block_data)
                decorrelation_samples_read = True
            if (metadata_function == 5):
                entropies = read_entropy_variables(block_header,
                                                   sub_block_data)
                entropies_read = True
            if (metadata_function == 9):
                (zero_bits,
                 one_bits,
                 duplicate_bits) = read_extended_integers(sub_block_data)
                extended_integers_read = True
            if (metadata_function == 10):
                if (not entropies_read):
                    raise ValueError("bitstream sub block before " +
                                     "entropy variables sub block")
                residuals = read_bitstream(block_header, entropies,
                                           sub_block_data)
                residuals_read = True

        if (large_sub_block == 0):
            sub_blocks_size -= (2 + 2 * sub_block_size)
        else:
            sub_blocks_size -= (4 + 2 * sub_block_size)

    if (decorrelation_terms_read):
        if (not decorrelation_weights_read):
            raise ValueError("decorrelation weights sub block not found")
        if (not decorrelation_samples_read):
            raise ValueError("decorrelation samples sub block not found")

    if (not residuals_read):
        raise ValueError("bitstream sub block not found")

    if ((block_header.mono_output == 0) and (block_header.false_stereo == 0)):
        if (decorrelation_terms_read and len(decorrelation_terms) > 0):
            decorrelated = decorrelate_channels(residuals,
                                                decorrelation_terms,
                                                decorrelation_deltas,
                                                decorrelation_weights,
                                                decorrelation_samples)
        else:
            decorrelated = residuals

        if (block_header.joint_stereo == 1):
            left_right = undo_joint_stereo(decorrelated)
        else:
            left_right = decorrelated

        channels_crc = calculate_crc(left_right)
        if (channels_crc != block_header.CRC):
            raise ValueError("CRC mismatch (0x%8.8X != 0x%8.8X)" %
                             (channels_crc, block_header.CRC))

        if (block_header.extended_size_integers == 1):
            un_shifted = undo_extended_integers(zero_bits,
                                                one_bits,
                                                duplicate_bits,
                                                left_right)
        else:
            un_shifted = left_right

        return un_shifted
    else:
        if (decorrelation_terms_read and len(decorrelation_terms) > 0):
            decorrelated = decorrelate_channels(residuals,
                                                decorrelation_terms,
                                                decorrelation_deltas,
                                                decorrelation_weights,
                                                decorrelation_samples)
        else:
            decorrelated = residuals

        channels_crc = calculate_crc(decorrelated)
        if (channels_crc != block_header.CRC):
            raise ValueError("CRC mismatch (0x%8.8X != 0x%8.8X)" %
                             (channels_crc, block_header.CRC))

        if (block_header.extended_size_integers == 1):
            un_shifted = undo_extended_integers(zero_bits,
                                                one_bits,
                                                duplicate_bits,
                                                decorrelated)
        else:
            un_shifted = decorrelated

        if (block_header.false_stereo == 0):
            return un_shifted
        else:
            return (un_shifted[0], un_shifted[0])


def read_decorrelation_terms(sub_block_size,
                             actual_size_1_less,
                             sub_block_data):
    """returns a list of decorrelation terms
    and a list of decorrelation deltas per decorrelation pass

    term[pass] , delta[pass]"""

    if (actual_size_1_less == 0):
        passes = sub_block_size * 2
    else:
        passes = sub_block_size * 2 - 1

    if (passes > 16):
        raise ValueError("invalid decorrelation passes count")

    decorrelation_terms = []
    decorrelation_deltas = []
    for i in xrange(passes):
        decorrelation_terms.append(sub_block_data.read(5) - 5)
        if (not (((1 <= decorrelation_terms[-1]) and
                  (decorrelation_terms[-1] <= 18)) or
                 ((-3 <= decorrelation_terms[-1]) and
                  (decorrelation_terms[-1] <= -1)))):
            raise ValueError("invalid decorrelation term")
        decorrelation_deltas.append(sub_block_data.read(3))

    decorrelation_terms.reverse()
    decorrelation_deltas.reverse()

    return (decorrelation_terms, decorrelation_deltas)


def read_decorrelation_weights(block_header, decorrelation_terms_count,
                               sub_block_size, actual_size_1_less,
                               sub_block_data):
    """returns one tuple of decorrelation weights per decorrelation pass
    the number of weights in each tuple equals the number of channels

    weight[pass][channel]
    """

    if (actual_size_1_less == 0):
        weight_count = sub_block_size * 2
    else:
        weight_count = sub_block_size * 2 - 1

    weight_values = []
    for i in xrange(weight_count):
        value_i = sub_block_data.read_signed(8)
        if (value_i > 0):
            weight_values.append((value_i * 2 ** 3) +
                                 ((value_i * 2 ** 3 + 2 ** 6) // 2 ** 7))
        elif(value_i == 0):
            weight_values.append(0)
        else:
            weight_values.append(value_i * 2 ** 3)

    weights = []
    if ((block_header.mono_output == 0) and (block_header.false_stereo == 0)):
        #two channels
        if ((weight_count // 2) > decorrelation_terms_count):
            raise ValueError("invalid number of decorrelation weights")

        for i in xrange(weight_count // 2):
            weights.append((weight_values[i * 2],
                            weight_values[i * 2 + 1]))
        for i in xrange(weight_count // 2, decorrelation_terms_count):
            weights.append((0, 0))

        weights.reverse()
    else:
        #one channel
        if (weight_count > decorrelation_terms_count):
            raise ValueError("invalid number of decorrelation weights")

        for i in xrange(weight_count):
            weights.append((weight_values[i], ))
        for i in xrange(weight_count, decorrelation_terms_count):
            weights.append((0, 0))
        weights.reverse()

    return weights


def read_decorrelation_samples(block_header, decorrelation_terms,
                               sub_block_size, sub_block_data):
    """returns one tuple of decorrelation samples lists
    per decorrelation pass

    sample[pass][channel][s]"""

    sub_block_bytes = sub_block_size * 2

    samples = []
    if ((block_header.mono_output == 0) and (block_header.false_stereo == 0)):
        #two channels
        for term in reversed(decorrelation_terms):
            if ((17 <= term) and (term <= 18)):
                if (sub_block_bytes >= 8):
                    samples.append(([read_exp2(sub_block_data),
                                     read_exp2(sub_block_data)],
                                    [read_exp2(sub_block_data),
                                     read_exp2(sub_block_data)]))
                    sub_block_bytes -= 8
                else:
                    samples.append(([0, 0], [0, 0]))
                    sub_block_bytes = 0
            elif ((1 <= term) and (term <= 8)):
                term_samples = ([], [])
                if (sub_block_bytes >= (term * 4)):
                    for s in xrange(term):
                        term_samples[0].append(read_exp2(sub_block_data))
                        term_samples[1].append(read_exp2(sub_block_data))
                    sub_block_bytes -= (term * 4)
                else:
                    for s in xrange(term):
                        term_samples[0].append(0)
                        term_samples[1].append(0)
                    sub_block_bytes = 0
                samples.append(term_samples)
            elif ((-3 <= term) and (term <= -1)):
                if (sub_block_bytes >= 4):
                    samples.append(([read_exp2(sub_block_data)],
                                    [read_exp2(sub_block_data)]))
                    sub_block_bytes -= 4
                else:
                    samples.append(([0], [0]))
                    sub_block_bytes = 0
            else:
                raise ValueError("invalid decorrelation term")

        samples.reverse()
        return samples
    else:
        #one channel
        for term in reversed(decorrelation_terms):
            if ((17 <= term) and (term <= 18)):
                if (sub_block_bytes >= 4):
                    samples.append(([read_exp2(sub_block_data),
                                     read_exp2(sub_block_data)],))
                    sub_block_bytes -= 4
                else:
                    samples[0].append(([0, 0],))
                    sub_block_bytes = 0
            elif ((1 <= term) and (term <= 8)):
                term_samples = ([],)
                if (sub_block_bytes >= (term * 2)):
                    for s in xrange(term):
                        term_samples[0].append(read_exp2(sub_block_data))
                    sub_block_bytes -= (term * 2)
                else:
                    for s in xrange(term):
                        term_samples[0].append(0)
                    sub_block_bytes = 0
                samples.append(term_samples)
            else:
                raise ValueError("invalid decorrelation term")

        samples.reverse()
        return samples


def read_entropy_variables(block_header, sub_block_data):
    entropies = ([], [])
    for i in xrange(3):
        entropies[0].append(read_exp2(sub_block_data))

    if ((block_header.mono_output == 0) and (block_header.false_stereo == 0)):
        for i in xrange(3):
            entropies[1].append(read_exp2(sub_block_data))
    else:
        entropies[1].extend([0, 0, 0])

    return entropies


def read_bitstream(block_header, entropies, sub_block_data):
    if ((block_header.mono_output == 0) and (block_header.false_stereo == 0)):
        channel_count = 2
        residuals = ([], [])
    else:
        channel_count = 1
        residuals = ([], )

    u = None
    i = 0
    while (i < (block_header.block_samples * channel_count)):
        if ((u is None) and (entropies[0][0] < 2) and (entropies[1][0] < 2)):
            #handle long run of 0 residuals
            zeroes = read_egc(sub_block_data)
            if (zeroes > 0):
                for j in xrange(zeroes):
                    residuals[i % channel_count].append(0)
                    i += 1
                entropies[0][0] = entropies[0][1] = entropies[0][2] = 0
                entropies[1][0] = entropies[1][1] = entropies[1][2] = 0
            if (i < (block_header.block_samples * channel_count)):
                (residual, u) = read_residual(
                    sub_block_data,
                    u,
                    entropies[i % channel_count])
                residuals[i % channel_count].append(residual)
                i += 1
        else:
            (residual, u) = read_residual(
                sub_block_data,
                u,
                entropies[i % channel_count])
            residuals[i % channel_count].append(residual)
            i += 1

    return residuals


def read_egc(reader):
    t = reader.unary(0)
    if (t > 0):
        p = reader.read(t - 1)
        return 2 ** (t - 1) + p
    else:
        return t


def read_residual(reader, last_u, entropies):
    if (last_u is None):
        u = reader.unary(0)
        if (u == 16):
            u += read_egc(reader)
        m = u // 2
    elif ((last_u % 2) == 1):
        u = reader.unary(0)
        if (u == 16):
            u += read_egc(reader)
        m = (u // 2) + 1
    else:
        u = None
        m = 0

    if (m == 0):
        base = 0
        add = entropies[0] >> 4
        entropies[0] -= ((entropies[0] + 126) >> 7) * 2
    elif (m == 1):
        base = (entropies[0] >> 4) + 1
        add = entropies[1] >> 4
        entropies[0] += ((entropies[0] + 128) >> 7) * 5
        entropies[1] -= ((entropies[1] + 62) >> 6) * 2
    elif (m == 2):
        base = ((entropies[0] >> 4) + 1) + ((entropies[1] >> 4) + 1)
        add = entropies[2] >> 4
        entropies[0] += ((entropies[0] + 128) >> 7) * 5
        entropies[1] += ((entropies[1] + 64) >> 6) * 5
        entropies[2] -= ((entropies[2] + 30) >> 5) * 2
    else:
        base = (((entropies[0] >> 4) + 1) +
                ((entropies[1] >> 4) + 1) +
                (((entropies[2] >> 4) + 1) * (m - 2)))
        add = entropies[2] >> 4
        entropies[0] += ((entropies[0] + 128) >> 7) * 5
        entropies[1] += ((entropies[1] + 64) >> 6) * 5
        entropies[2] += ((entropies[2] + 32) >> 5) * 5

    if (add == 0):
        unsigned = base
    else:
        p = int(log(add) / log(2))
        e = 2 ** (p + 1) - add - 1
        r = reader.read(p)
        if (r >= e):
            b = reader.read(1)
            unsigned = base + (r * 2) - e + b
        else:
            unsigned = base + r

    sign = reader.read(1)
    if (sign == 1):
        return (-unsigned - 1, u)
    else:
        return (unsigned, u)


def undo_joint_stereo(samples):
    assert(len(samples) == 2)
    assert(len(samples[0]) == len(samples[1]))

    stereo = [[], []]
    for (mid, side) in zip(*samples):
        right = side - (mid >> 1)
        left = mid + right
        stereo[0].append(left)
        stereo[1].append(right)

    return stereo


def read_extended_integers(sub_block_data):
    (sent_bits,
     zero_bits,
     one_bits,
     duplicate_bits) = sub_block_data.parse("8u 8u 8u 8u")
    return (zero_bits, one_bits, duplicate_bits)


def undo_extended_integers(zero_bits, one_bits, duplicate_bits,
                           channels):
    un_shifted = []
    for channel in channels:
        if (zero_bits > 0):
            un_shifted.append([s << zero_bits for s in channel])
        elif (one_bits > 0):
            ones = (1 << one_bits) - 1
            un_shifted.append([(s << one_bits) + ones for s in channel])
        elif (duplicate_bits > 0):
            dupes = []
            ones = (1 << duplicate_bits) - 1
            for s in channel:
                if ((s % 2) == 0):
                    dupes.append(s << duplicate_bits)
                else:
                    dupes.append((s << duplicate_bits) + ones)
            un_shifted.append(dupes)
        else:
            un_shifted.append(channel)

    return tuple(un_shifted)


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


def decorrelate_channels(residuals,
                         decorrelation_terms, decorrelation_deltas,
                         decorrelation_weights, decorrelation_samples):
    """returns a tuple of 1 or 2 lists of decorrelated channel data"""

    if (len(residuals) == 2):
        latest_pass = [r[:] for r in residuals]
        for (term,
             delta,
             weights,
             samples) in zip(decorrelation_terms,
                             decorrelation_deltas,
                             decorrelation_weights,
                             decorrelation_samples):
            latest_pass = decorrelation_pass_2ch(latest_pass,
                                                 term,
                                                 delta,
                                                 weights,
                                                 samples)
        return latest_pass
    else:
        latest_pass = residuals[0][:]
        for (term,
             delta,
             weight,
             samples) in zip(decorrelation_terms,
                             decorrelation_deltas,
                             decorrelation_weights,
                             decorrelation_samples):
            latest_pass = decorrelation_pass_1ch(latest_pass,
                                                 term,
                                                 delta,
                                                 weight[0],
                                                 samples[0])
        return (latest_pass, )


def decorrelation_pass_1ch(correlated_samples,
                           term, delta, weight, decorrelation_samples):
    if (term == 18):
        assert(len(decorrelation_samples) == 2)
        decorrelated = decorrelation_samples[:]
        decorrelated.reverse()
        for i in xrange(len(correlated_samples)):
            temp = (3 * decorrelated[i + 1] - decorrelated[i]) // 2
            decorrelated.append(apply_weight(weight, temp) +
                                correlated_samples[i])
            weight += update_weight(temp, correlated_samples[i], delta)
        return decorrelated[2:]
    elif (term == 17):
        assert(len(decorrelation_samples) == 2)
        decorrelated = decorrelation_samples[:]
        decorrelated.reverse()
        for i in xrange(len(correlated_samples)):
            temp = 2 * decorrelated[i + 1] - decorrelated[i]
            decorrelated.append(apply_weight(weight, temp) +
                                correlated_samples[i])
            weight += update_weight(temp, correlated_samples[i], delta)
        return decorrelated[2:]
    elif ((1 <= term) and (term <= 8)):
        assert(len(decorrelation_samples) == term)
        decorrelated = decorrelation_samples[:]
        for i in xrange(len(correlated_samples)):
            decorrelated.append(apply_weight(weight, decorrelated[i]) +
                                correlated_samples[i])
            weight += update_weight(decorrelated[i],
                                    correlated_samples[i],
                                    delta)
        return decorrelated[term:]
    else:
        raise ValueError("unsupported term")


def decorrelation_pass_2ch(correlated,
                           term, delta, weights, decorrelation_samples):
    assert(len(correlated) == 2)
    assert(len(correlated[0]) == len(correlated[1]))
    assert(len(weights) == 2)

    if (((17 <= term) and (term <= 18)) or ((1 <= term) and (term <= 8))):
        return (decorrelation_pass_1ch(correlated[0],
                                       term, delta, weights[0],
                                       decorrelation_samples[0]),
                decorrelation_pass_1ch(correlated[1],
                                       term, delta, weights[1],
                                       decorrelation_samples[1]))
    elif ((-3 <= term) and (term <= -1)):
        assert(len(decorrelation_samples[0]) == 1)
        decorrelated = ([decorrelation_samples[1][0]],
                        [decorrelation_samples[0][0]])
        weights = list(weights)
        if (term == -1):
            for i in xrange(len(correlated[0])):
                decorrelated[0].append(apply_weight(weights[0],
                                                    decorrelated[1][i]) +
                                       correlated[0][i])
                decorrelated[1].append(apply_weight(weights[1],
                                                    decorrelated[0][i + 1]) +
                                       correlated[1][i])

                weights[0] += update_weight(decorrelated[1][i],
                                            correlated[0][i],
                                            delta)
                weights[1] += update_weight(decorrelated[0][i + 1],
                                            correlated[1][i],
                                            delta)
                weights[0] = max(min(weights[0], 1024), -1024)
                weights[1] = max(min(weights[1], 1024), -1024)
        elif (term == -2):
            for i in xrange(len(correlated[0])):
                decorrelated[1].append(apply_weight(weights[1],
                                                    decorrelated[0][i]) +
                                       correlated[1][i])
                decorrelated[0].append(apply_weight(weights[0],
                                                    decorrelated[1][i + 1]) +
                                       correlated[0][i])

                weights[1] += update_weight(decorrelated[0][i],
                                            correlated[1][i],
                                            delta)

                weights[0] += update_weight(decorrelated[1][i + 1],
                                            correlated[0][i],
                                            delta)
                weights[1] = max(min(weights[1], 1024), -1024)
                weights[0] = max(min(weights[0], 1024), -1024)
        elif (term == -3):
            for i in xrange(len(correlated[0])):
                decorrelated[0].append(apply_weight(weights[0],
                                                    decorrelated[1][i]) +
                                       correlated[0][i])
                decorrelated[1].append(apply_weight(weights[1],
                                                    decorrelated[0][i]) +
                                       correlated[1][i])

                weights[0] += update_weight(decorrelated[1][i],
                                            correlated[0][i],
                                            delta)
                weights[1] += update_weight(decorrelated[0][i],
                                            correlated[1][i],
                                            delta)
                weights[0] = max(min(weights[0], 1024), -1024)
                weights[1] = max(min(weights[1], 1024), -1024)

        assert(len(decorrelated[0]) == len(decorrelated[1]))
        return (decorrelated[0][1:], decorrelated[1][1:])
    else:
        raise ValueError("unsupported term")


def apply_weight(weight, sample):
    return ((weight * sample) + 512) >> 10


def update_weight(source, result, delta):
    if ((source == 0) or (result == 0)):
        return 0
    elif ((source ^ result) >= 0):
        return delta
    else:
        return -delta


def calculate_crc(samples):
    crc = 0xFFFFFFFF

    for frame in zip(*samples):
        for s in frame:
            crc = 3 * crc + s

    if (crc >= 0):
        return crc % 0x100000000
    else:
        return (2 ** 32 - (-crc)) % 0x100000000
