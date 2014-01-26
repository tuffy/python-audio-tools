#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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

from audiotools.bitstream import BitstreamWriter
from audiotools.bitstream import BitstreamRecorder
from audiotools.bitstream import BitstreamAccumulator
from audiotools import BufferedPCMReader
from hashlib import md5


class STREAMINFO:
    def __init__(self, minimum_block_size, maximum_block_size,
                 minimum_frame_size, maximum_frame_size,
                 sample_rate, channels, bits_per_sample,
                 total_pcm_frames, md5sum):
        self.minimum_block_size = minimum_block_size
        self.maximum_block_size = maximum_block_size
        self.minimum_frame_size = minimum_frame_size
        self.maximum_frame_size = maximum_frame_size
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.total_pcm_frames = total_pcm_frames
        self.md5sum = md5sum

    def write(self, writer):
        writer.build("16u 16u 24u 24u 20u 3u 5u 36U 16b",
                     [self.minimum_block_size,
                      self.maximum_block_size,
                      self.minimum_frame_size,
                      self.maximum_frame_size,
                      self.sample_rate,
                      self.channels - 1,
                      self.bits_per_sample - 1,
                      self.total_pcm_frames,
                      self.md5sum.digest()])

    def input_update(self, framelist):
        self.total_pcm_frames += framelist.frames
        self.md5sum.update(framelist.to_bytes(False, True))

    def output_update(self, flac_frame):
        self.minimum_frame_size = min(self.minimum_frame_size,
                                      flac_frame.bytes())
        self.maximum_frame_size = max(self.maximum_frame_size,
                                      flac_frame.bytes())


class Encoding_Options:
    def __init__(self, block_size=4096, max_lpc_order=8,
                 adaptive_mid_side=False, mid_side=True,
                 exhaustive_model_search=False,
                 max_residual_partition_order=5,
                 max_rice_parameter=14):
        self.block_size = block_size
        self.max_lpc_order = max_lpc_order
        self.adaptive_mid_side = adaptive_mid_side
        self.mid_side = mid_side
        self.exhaustive_model_search = exhaustive_model_search
        self.max_residual_partition_order = max_residual_partition_order
        self.max_rice_parameter = max_rice_parameter

        if (block_size <= 192):
            self.qlp_precision = 7
        elif (block_size <= 384):
            self.qlp_precision = 8
        elif (block_size <= 576):
            self.qlp_precision = 9
        elif (block_size <= 1152):
            self.qlp_precision = 10
        elif (block_size <= 2304):
            self.qlp_precision = 11
        elif (block_size <= 4608):
            self.qlp_precision = 12
        else:
            self.qlp_precision = 13


def encode_flac(filename,
                pcmreader,
                block_size=4096,
                max_lpc_order=8,
                min_residual_partition_order=0,
                max_residual_partition_order=5,
                mid_side=True,
                adaptive_mid_side=False,
                exhaustive_model_search=False,
                disable_verbatim_subframes=False,
                disable_constant_subframes=False,
                disable_fixed_subframes=False,
                disable_lpc_subframes=False):

    current_offset = 0
    frame_offsets = []

    options = Encoding_Options(block_size,
                               max_lpc_order,
                               adaptive_mid_side,
                               mid_side,
                               exhaustive_model_search,
                               max_residual_partition_order,
                               14 if pcmreader.bits_per_sample <= 16 else 30)

    streaminfo = STREAMINFO(block_size,
                            block_size,
                            (2 ** 24) - 1,
                            0,
                            pcmreader.sample_rate,
                            pcmreader.channels,
                            pcmreader.bits_per_sample,
                            0, md5())

    pcmreader = BufferedPCMReader(pcmreader)
    output_file = open(filename, "wb")
    writer = BitstreamWriter(output_file, 0)

    #write placeholder metadata blocks
    writer.write_bytes("fLaC")
    writer.build("1u 7u 24u", [1, 0, 34])
    streaminfo.write(writer)

    #walk through PCM reader's FrameLists
    frame_number = 0
    frame = pcmreader.read(block_size)

    flac_frame = BitstreamRecorder(0)

    while (len(frame) > 0):
        frame_offsets.append((current_offset, frame.frames))
        streaminfo.input_update(frame)

        flac_frame.reset()
        encode_flac_frame(flac_frame, pcmreader, options, frame_number, frame)
        current_offset += flac_frame.bytes()
        streaminfo.output_update(flac_frame)

        flac_frame.copy(writer)

        frame_number += 1
        frame = pcmreader.read(block_size)

    #return to beginning of file and rewrite STREAMINFO block
    output_file.seek(8, 0)
    streaminfo.write(writer)
    writer.close()

    return frame_offsets


def encode_flac_frame(writer, pcmreader, options, frame_number, frame):
    crc16 = CRC16()
    writer.add_callback(crc16.update)

    if ((pcmreader.channels == 2) and (options.adaptive_mid_side or
                                       options.mid_side)):
        #calculate average/difference
        average = [(c0 + c1) / 2 for c0, c1 in zip(frame.channel(0),
                                                   frame.channel(1))]
        difference = [c0 - c1 for c0, c1 in zip(frame.channel(0),
                                                frame.channel(1))]

        #try different subframes based on encoding options
        left_subframe = BitstreamRecorder(0)
        encode_subframe(left_subframe, options,
                        pcmreader.bits_per_sample, list(frame.channel(0)))

        right_subframe = BitstreamRecorder(0)
        encode_subframe(right_subframe, options,
                        pcmreader.bits_per_sample, list(frame.channel(1)))

        average_subframe = BitstreamRecorder(0)
        encode_subframe(average_subframe, options,
                        pcmreader.bits_per_sample, average)

        difference_subframe = BitstreamRecorder(0)
        encode_subframe(difference_subframe, options,
                        pcmreader.bits_per_sample + 1, difference)

        #write best header/subframes to disk
        if (options.mid_side):
            if ((left_subframe.bits() + right_subframe.bits()) <
                min(left_subframe.bits() + difference_subframe.bits(),
                    difference_subframe.bits() + right_subframe.bits(),
                    average_subframe.bits() + difference_subframe.bits())):
                write_frame_header(writer, pcmreader, frame_number, frame, 0x1)
                left_subframe.copy(writer)
                right_subframe.copy(writer)
            elif (left_subframe.bits() <
                  min(right_subframe.bits(), difference_subframe.bits())):
                write_frame_header(writer, pcmreader, frame_number, frame, 0x8)
                left_subframe.copy(writer)
                difference_subframe.copy(writer)
            elif (right_subframe.bits() < average_subframe.bits()):
                write_frame_header(writer, pcmreader, frame_number, frame, 0x9)
                difference_subframe.copy(writer)
                right_subframe.copy(writer)
            else:
                write_frame_header(writer, pcmreader, frame_number, frame, 0xA)
                average_subframe.copy(writer)
                difference_subframe.copy(writer)
        else:
            if (((left_subframe.bits() + right_subframe.bits()) <
                 (average_subframe.bits() + difference_subframe.bits()))):
                write_frame_header(writer, pcmreader, frame_number, frame, 0x1)
                left_subframe.copy(writer)
                right_subframe.copy(writer)
            else:
                write_frame_header(writer, pcmreader, frame_number, frame, 0xA)
                average_subframe.copy(writer)
                difference_subframe.copy(writer)
    else:
        write_frame_header(writer, pcmreader, frame_number, frame,
                           pcmreader.channels - 1)

        for i in xrange(frame.channels):
            encode_subframe(writer,
                            options,
                            pcmreader.bits_per_sample,
                            list(frame.channel(i)))

    writer.byte_align()
    writer.pop_callback()
    writer.write(16, int(crc16))


def write_frame_header(writer, pcmreader, frame_number, frame,
                       channel_assignment):
    crc8 = CRC8()
    writer.add_callback(crc8.update)
    writer.write(14, 0x3FFE)
    writer.write(1, 0)
    writer.write(1, 0)
    encoded_block_size = {192: 1,
                          256: 8,
                          512: 9,
                          576: 2,
                          1024: 10,
                          1152: 3,
                          2048: 11,
                          2304: 4,
                          4096: 12,
                          4608: 5,
                          8192: 13,
                          16384: 14,
                          32768: 15}.get(frame.frames, None)
    if (encoded_block_size is None):
        if (frame.frames <= 256):
            encoded_block_size = 6
        elif (frame.frames <= 65536):
            encoded_block_size = 7
        else:
            encoded_block_size = 0
    writer.write(4, encoded_block_size)

    encoded_sample_rate = {8000: 4,
                           16000: 5,
                           22050: 6,
                           24000: 7,
                           32000: 8,
                           44100: 9,
                           48000: 10,
                           88200: 1,
                           96000: 11,
                           176400: 2,
                           192000: 3}.get(pcmreader.sample_rate, None)
    if (encoded_sample_rate is None):
        if ((((pcmreader.sample_rate % 1000) == 0) and
             (pcmreader.sample_rate <= 255000))):
            encoded_sample_rate = 12
        elif (((pcmreader.sample_rate % 10) == 0) and
              (pcmreader.sample_rate <= 655350)):
            encoded_sample_rate = 14
        elif (pcmreader.sample_rate <= 65535):
            encoded_sample_rate = 13
        else:
            encoded_sample_rate = 0
    writer.write(4, encoded_sample_rate)

    writer.write(4, channel_assignment)

    encoded_bps = {8: 1,
                   12: 2,
                   16: 4,
                   20: 5,
                   24: 6}.get(pcmreader.bits_per_sample, 0)
    writer.write(3, encoded_bps)

    writer.write(1, 0)
    write_utf8(writer, frame_number)

    if (encoded_block_size == 6):
        writer.write(8, frame.frames - 1)
    elif (encoded_block_size == 7):
        writer.write(16, frame.frames - 1)

    if (encoded_sample_rate == 12):
        writer.write(8, pcmreader.sample_rate % 1000)
    elif (encoded_sample_rate == 13):
        writer.write(16, pcmreader.sample_rate)
    elif (encoded_sample_rate == 14):
        writer.write(16, pcmreader.sample_rate % 10)

    writer.pop_callback()
    writer.write(8, int(crc8))


def write_utf8(writer, value):
    if (value <= 127):
        writer.write(8, value)
    else:
        if (value <= 2047):
            total_bytes = 2
        elif (value <= 65535):
            total_bytes = 3
        elif (value <= 2097151):
            total_bytes = 4
        elif (value <= 67108863):
            total_bytes = 5
        elif (value <= 2147483647):
            total_bytes = 6
        else:
            raise ValueError("UTF-8 value too large")

        shift = (total_bytes - 1) * 6
        writer.unary(0, total_bytes)
        writer.write(7 - total_bytes, value >> shift)
        shift -= 6
        while (shift >= 0):
            writer.write(2, 2)
            writer.write(6, (value >> shift) & 0x3F)
            shift -= 6


def encode_subframe(writer, options, bits_per_sample, samples):
    def all_identical(l):
        if (len(l) == 1):
            return True
        else:
            for i in l[1:]:
                if (i != l[0]):
                    return False
            else:
                return True

    def wasted(s):
        w = 0
        while ((s & 1) == 0):
            w += 1
            s >>= 1
        return w

    if (all_identical(samples)):
        encode_constant_subframe(writer, bits_per_sample, samples[0])
    else:
        #account for wasted BPS, if any
        wasted_bps = 2 ** 32
        for sample in samples:
            if (sample != 0):
                wasted_bps = min(wasted_bps, wasted(sample))
                if (wasted_bps == 0):
                    break

        if (wasted_bps == 2 ** 32):
            #all samples are 0
            wasted_bps = 0
        elif (wasted_bps > 0):
            samples = [s >> wasted_bps for s in samples]

        fixed_subframe = BitstreamRecorder(0)
        encode_fixed_subframe(fixed_subframe,
                              options,
                              wasted_bps,
                              bits_per_sample,
                              samples)

        if (options.max_lpc_order > 0):
            (lpc_order,
             qlp_coeffs,
             qlp_shift_needed) = compute_lpc_coefficients(options,
                                                          wasted_bps,
                                                          bits_per_sample,
                                                          samples)

            lpc_subframe = BitstreamRecorder(0)
            encode_lpc_subframe(lpc_subframe,
                                options,
                                wasted_bps,
                                bits_per_sample,
                                lpc_order,
                                options.qlp_precision,
                                qlp_shift_needed,
                                qlp_coeffs,
                                samples)

            if (((bits_per_sample * len(samples)) <
                 min(fixed_subframe.bits(), lpc_subframe.bits()))):
                encode_verbatim_subframe(writer, wasted_bps,
                                         bits_per_sample, samples)
            elif (fixed_subframe.bits() < lpc_subframe.bits()):
                fixed_subframe.copy(writer)
            else:
                lpc_subframe.copy(writer)
        else:
            if ((bits_per_sample * len(samples)) < fixed_subframe.bits()):
                encode_verbatim_subframe(writer, wasted_bps,
                                         bits_per_sample, samples)
            else:
                fixed_subframe.copy(writer)


def encode_constant_subframe(writer, bits_per_sample, sample):
    #write frame header
    writer.build("1p 6u 1u", [0, 0])

    #write frame data
    writer.write_signed(bits_per_sample, sample)


def encode_verbatim_subframe(writer, wasted_bps, bits_per_sample, samples):
    #write frame header
    writer.build("1p 6u", [1])
    if (wasted_bps > 0):
        writer.write(1, 1)
        writer.unary(1, wasted_bps - 1)
    else:
        writer.write(1, 0)

    #write frame data
    writer.build(("%ds" % (bits_per_sample - wasted_bps)) * len(samples),
                 samples)


def encode_fixed_subframe(writer, options, wasted_bps, bits_per_sample,
                          samples):
    def next_order(residuals):
        return [(x - y) for (x, y) in zip(residuals[1:], residuals)]

    #decide which subframe order to use
    residuals = [samples]
    total_error = [sum(map(abs, residuals[-1][4:]))]

    if (len(samples) > 4):
        for order in xrange(1, 5):
            residuals.append(next_order(residuals[-1]))
            total_error.append(sum(map(abs, residuals[-1][4 - order:])))

        for order in xrange(4):
            if (total_error[order] < min(total_error[order + 1:])):
                break
        else:
            order = 4
    else:
        order = 0

    #then write the subframe to disk

    #write subframe header
    writer.build("1p 3u 3u", [1, order])
    if (wasted_bps > 0):
        writer.write(1, 1)
        writer.unary(1, wasted_bps - 1)
    else:
        writer.write(1, 0)

    #write warm-up samples
    for sample in samples[0:order]:
        writer.write_signed(bits_per_sample - wasted_bps, sample)

    #write residual block
    encode_residuals(writer, options, order, len(samples), residuals[order])


def encode_residuals(writer, options, order, block_size, residuals):
    #first, determine the best set of residual partitions to use
    best_porder = 0
    best_size = 2 ** 31

    for porder in xrange(0, options.max_residual_partition_order + 1):
        if ((block_size % (2 ** porder)) == 0):
            unencoded_residuals = residuals[:]
            partitions = []
            for p in xrange(0, 2 ** porder):
                if (p == 0):
                    partition_size = block_size / (2 ** porder) - order
                else:
                    partition_size = block_size / (2 ** porder)
                partitions.append(unencoded_residuals[0:partition_size])
                unencoded_residuals = unencoded_residuals[partition_size:]

            rice_parameters = [best_rice_parameter(options, p)
                               for p in partitions]

            encoded_partitions = [encode_residual_partition(r, p)
                                  for (r, p) in zip(rice_parameters,
                                                    partitions)]

            partition_bit_size = sum([4 + p.bits()
                                      for p in encoded_partitions])

            if (partition_bit_size < best_size):
                best_porder = porder
                best_size = partition_bit_size
                best_parameters = rice_parameters
                best_encoded_partitions = encoded_partitions

    #then output those residual partitions into a single block
    if (max(best_parameters) > 14):
        coding_method = 1
    else:
        coding_method = 0

    writer.write(2, coding_method)
    writer.write(4, best_porder)
    for (rice, partition) in zip(best_parameters, best_encoded_partitions):
        if (coding_method == 0):
            writer.write(4, rice)
        else:
            writer.write(5, rice)
        partition.copy(writer)


def best_rice_parameter(options, residuals):
    partition_sum = sum(map(abs, residuals))
    rice_parameter = 0
    while ((len(residuals) * (2 ** rice_parameter)) < partition_sum):
        if (rice_parameter < options.max_rice_parameter):
            rice_parameter += 1
        else:
            return options.max_rice_parameter

    return rice_parameter


def encode_residual_partition(rice_parameter, residuals):
    partition = BitstreamRecorder(0)
    for residual in residuals:
        if (residual >= 0):
            unsigned = residual << 1
        else:
            unsigned = ((-residual - 1) << 1) | 1
        MSB = unsigned >> rice_parameter
        LSB = unsigned - (MSB << rice_parameter)
        partition.unary(1, MSB)
        partition.write(rice_parameter, LSB)

    return partition


def tukey_window(sample_count, alpha):
    from math import cos, pi

    window1 = (alpha * (sample_count - 1)) / 2
    window2 = (sample_count - 1) * (1 - (alpha / 2))

    for n in xrange(0, sample_count):
        if (n <= window1):
            yield (0.5 *
                   (1 +
                    cos(pi * (((2 * n) / (alpha * (sample_count - 1))) - 1))))
        elif (n <= window2):
            yield 1.0
        else:
            yield (0.5 *
                   (1 +
                    cos(pi * (((2 * n) / (alpha * (sample_count - 1))) -
                              (2 / alpha) + 1))))


def compute_lpc_coefficients(options, wasted_bps, bits_per_sample, samples):
    """returns a (order, qlp_coeffs, qlp_shift_needed) triple
    where order is an int
    where qlp_coeffs is a list of ints (whose length equals order)
    and qlp_shift_needed is a non-negative integer"""

    #window signal
    windowed = [(sample * tukey) for (sample, tukey) in
                zip(samples, tukey_window(len(samples), 0.5))]

    #compute autocorrelation values
    if (len(samples) > (options.max_lpc_order + 1)):
        autocorrelation_values = [
            sum([x * y for x, y in zip(windowed, windowed[lag:])])
            for lag in xrange(0, options.max_lpc_order + 1)]

        if ((len(autocorrelation_values) > 1) and
            (set(autocorrelation_values) !=
             set([0.0]))):
            (lp_coefficients,
             error) = compute_lp_coefficients(autocorrelation_values)

            if (not options.exhaustive_model_search):
                #if not performing exhaustive model search,
                #estimate which set of LP coefficients is best
                #and return those

                order = estimate_best_lpc_order(options,
                                                len(samples),
                                                bits_per_sample,
                                                error)
                (qlp_coeffs,
                 qlp_shift_needed) = quantize_coefficients(
                     options.qlp_precision,
                     lp_coefficients,
                     order)

                return (order, qlp_coeffs, qlp_shift_needed)
            else:
                #if performing exhaustive model search,
                #build LPC subframe from each set of LP coefficients
                #and return the one that is smallest

                best_subframe_size = 2 ** 32
                best_order = None
                best_coeffs = None
                best_shift_needed = None
                for order in xrange(1, options.max_lpc_order + 1):
                    (qlp_coeffs,
                     qlp_shift_needed) = quantize_coefficients(
                         options.qlp_precision, lp_coefficients, order)

                    subframe = BitstreamAccumulator(0)
                    encode_lpc_subframe(subframe, options,
                                        wasted_bps, bits_per_sample,
                                        order, options.qlp_precision,
                                        qlp_shift_needed, qlp_coeffs, samples)
                    if (subframe.bits() < best_subframe_size):
                        best_subframe_size = subframe.bits()
                        best_order = order
                        best_coeffs = qlp_coeffs
                        best_shift_needed = qlp_shift_needed

                return (best_order, best_coeffs, best_shift_needed)
        else:
            return (1, [0], 0)
    else:
        return (1, [0], 0)


def compute_lp_coefficients(autocorrelation):
    maximum_lpc_order = len(autocorrelation) - 1

    k0 = autocorrelation[1] / autocorrelation[0]
    lp_coefficients = [[k0]]
    error = [autocorrelation[0] * (1 - k0 ** 2)]

    for i in xrange(1, maximum_lpc_order):
        ki = (autocorrelation[i + 1] -
              sum([x * y for (x, y) in
                   zip(lp_coefficients[i - 1],
                       reversed(autocorrelation[1:i + 1]))])) / error[i - 1]

        lp_coefficients.append([c1 - (ki * c2) for (c1, c2) in
                                zip(lp_coefficients[i - 1],
                                    reversed(lp_coefficients[i - 1]))] + [ki])
        error.append(error[i - 1] * (1 - ki ** 2))

    return (lp_coefficients, error)


def estimate_best_lpc_order(options, block_size, bits_per_sample, error):
    """returns an order integer of the best LPC order to use"""

    from math import log

    error_scale = log(2) ** 2
    best_order = 0
    best_subframe_bits = 1e32
    for i in xrange(options.max_lpc_order):
        order = i + 1
        if (error[i] > 0.0):
            header_bits = order * (bits_per_sample + options.qlp_precision)
            bits_per_residual = max((log(error[i] * error_scale) /
                                     (log(2) * 2)), 0.0)
            estimated_subframe_bits = (header_bits +
                                       bits_per_residual *
                                       (block_size - order))
            if (estimated_subframe_bits < best_subframe_bits):
                best_order = order
                best_subframe_bits = estimated_subframe_bits
        elif (error[i] == 0.0):
            return order
    else:
        return best_order


def quantize_coefficients(qlp_precision, lp_coefficients, order):
    """returns a (qlp_coeffs, qlp_shift_needed) pair
    where qlp_coeffs is a list of ints
    and qlp_shift_needed is a non-negative integer"""

    from math import log

    l = max(map(abs, lp_coefficients[order - 1]))
    if (l > 0):
        qlp_shift_needed = min((qlp_precision - 1) -
                               (int(log(l) / log(2)) - 1) - 1,
                               (2 ** 4) - 1)
    else:
        qlp_shift_needed = 0
    if (qlp_shift_needed < -(2 ** 4)):
        raise ValueError("too much negative shift needed")

    qlp_max = 2 ** (qlp_precision - 1) - 1
    qlp_min = -(2 ** (qlp_precision - 1))
    error = 0.0
    qlp_coeffs = []

    if (qlp_shift_needed >= 0):
        for lp_coeff in lp_coefficients[order - 1]:
            error += (lp_coeff * 2 ** qlp_shift_needed)
            qlp_coeffs.append(min(max(int(round(error)), qlp_min), qlp_max))
            error -= qlp_coeffs[-1]

        return (qlp_coeffs, qlp_shift_needed)
    else:
        for lp_coeff in lp_coefficients[order - 1]:
            error += (lp_coeff / 2 ** -qlp_shift_needed)
            qlp_coeffs.append(min(max(int(round(error)), qlp_min), qlp_max))
            error -= qlp_coeffs[-1]

        return (qlp_coeffs, 0)


def encode_lpc_subframe(writer, options, wasted_bps, bits_per_sample,
                        order, qlp_precision, qlp_shift_needed,
                        qlp_coefficients, samples):
    assert(order == len(qlp_coefficients))
    assert(qlp_shift_needed >= 0)

    #write subframe header
    writer.build("1p 1u 5u", [1, order - 1])
    if (wasted_bps > 0):
        writer.write(1, 1)
        writer.unary(1, wasted_bps - 1)
    else:
        writer.write(1, 0)

    #write warm-up samples
    for sample in samples[0:order]:
        writer.write_signed(bits_per_sample - wasted_bps, sample)

    #write precision and shift-needed
    writer.build("4u 5s", (qlp_precision - 1, qlp_shift_needed))

    #write QLP coefficients
    for qlp_coeff in qlp_coefficients:
        writer.write_signed(qlp_precision, qlp_coeff)

    #calculate residuals
    residuals = []
    coefficients = list(reversed(qlp_coefficients))

    for (i, sample) in enumerate(samples[order:]):
        residuals.append(sample - (sum([c * s for c, s in
                                        zip(coefficients,
                                            samples[i:i + order])]) >>
                                   qlp_shift_needed))

    #write residual block
    encode_residuals(writer, options, order, len(samples), residuals)


class CRC8:
    TABLE = [0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15,
             0x38, 0x3F, 0x36, 0x31, 0x24, 0x23, 0x2A, 0x2D,
             0x70, 0x77, 0x7E, 0x79, 0x6C, 0x6B, 0x62, 0x65,
             0x48, 0x4F, 0x46, 0x41, 0x54, 0x53, 0x5A, 0x5D,
             0xE0, 0xE7, 0xEE, 0xE9, 0xFC, 0xFB, 0xF2, 0xF5,
             0xD8, 0xDF, 0xD6, 0xD1, 0xC4, 0xC3, 0xCA, 0xCD,
             0x90, 0x97, 0x9E, 0x99, 0x8C, 0x8B, 0x82, 0x85,
             0xA8, 0xAF, 0xA6, 0xA1, 0xB4, 0xB3, 0xBA, 0xBD,
             0xC7, 0xC0, 0xC9, 0xCE, 0xDB, 0xDC, 0xD5, 0xD2,
             0xFF, 0xF8, 0xF1, 0xF6, 0xE3, 0xE4, 0xED, 0xEA,
             0xB7, 0xB0, 0xB9, 0xBE, 0xAB, 0xAC, 0xA5, 0xA2,
             0x8F, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9D, 0x9A,
             0x27, 0x20, 0x29, 0x2E, 0x3B, 0x3C, 0x35, 0x32,
             0x1F, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0D, 0x0A,
             0x57, 0x50, 0x59, 0x5E, 0x4B, 0x4C, 0x45, 0x42,
             0x6F, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7D, 0x7A,
             0x89, 0x8E, 0x87, 0x80, 0x95, 0x92, 0x9B, 0x9C,
             0xB1, 0xB6, 0xBF, 0xB8, 0xAD, 0xAA, 0xA3, 0xA4,
             0xF9, 0xFE, 0xF7, 0xF0, 0xE5, 0xE2, 0xEB, 0xEC,
             0xC1, 0xC6, 0xCF, 0xC8, 0xDD, 0xDA, 0xD3, 0xD4,
             0x69, 0x6E, 0x67, 0x60, 0x75, 0x72, 0x7B, 0x7C,
             0x51, 0x56, 0x5F, 0x58, 0x4D, 0x4A, 0x43, 0x44,
             0x19, 0x1E, 0x17, 0x10, 0x05, 0x02, 0x0B, 0x0C,
             0x21, 0x26, 0x2F, 0x28, 0x3D, 0x3A, 0x33, 0x34,
             0x4E, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5C, 0x5B,
             0x76, 0x71, 0x78, 0x7F, 0x6A, 0x6D, 0x64, 0x63,
             0x3E, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2C, 0x2B,
             0x06, 0x01, 0x08, 0x0F, 0x1A, 0x1D, 0x14, 0x13,
             0xAE, 0xA9, 0xA0, 0xA7, 0xB2, 0xB5, 0xBC, 0xBB,
             0x96, 0x91, 0x98, 0x9F, 0x8A, 0x8D, 0x84, 0x83,
             0xDE, 0xD9, 0xD0, 0xD7, 0xC2, 0xC5, 0xCC, 0xCB,
             0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3]

    def __init__(self):
        self.value = 0

    def __int__(self):
        return self.value

    def update(self, byte):
        self.value = self.TABLE[self.value ^ byte]


class CRC16(CRC8):
    TABLE = [0x0000, 0x8005, 0x800f, 0x000a, 0x801b, 0x001e, 0x0014, 0x8011,
             0x8033, 0x0036, 0x003c, 0x8039, 0x0028, 0x802d, 0x8027, 0x0022,
             0x8063, 0x0066, 0x006c, 0x8069, 0x0078, 0x807d, 0x8077, 0x0072,
             0x0050, 0x8055, 0x805f, 0x005a, 0x804b, 0x004e, 0x0044, 0x8041,
             0x80c3, 0x00c6, 0x00cc, 0x80c9, 0x00d8, 0x80dd, 0x80d7, 0x00d2,
             0x00f0, 0x80f5, 0x80ff, 0x00fa, 0x80eb, 0x00ee, 0x00e4, 0x80e1,
             0x00a0, 0x80a5, 0x80af, 0x00aa, 0x80bb, 0x00be, 0x00b4, 0x80b1,
             0x8093, 0x0096, 0x009c, 0x8099, 0x0088, 0x808d, 0x8087, 0x0082,
             0x8183, 0x0186, 0x018c, 0x8189, 0x0198, 0x819d, 0x8197, 0x0192,
             0x01b0, 0x81b5, 0x81bf, 0x01ba, 0x81ab, 0x01ae, 0x01a4, 0x81a1,
             0x01e0, 0x81e5, 0x81ef, 0x01ea, 0x81fb, 0x01fe, 0x01f4, 0x81f1,
             0x81d3, 0x01d6, 0x01dc, 0x81d9, 0x01c8, 0x81cd, 0x81c7, 0x01c2,
             0x0140, 0x8145, 0x814f, 0x014a, 0x815b, 0x015e, 0x0154, 0x8151,
             0x8173, 0x0176, 0x017c, 0x8179, 0x0168, 0x816d, 0x8167, 0x0162,
             0x8123, 0x0126, 0x012c, 0x8129, 0x0138, 0x813d, 0x8137, 0x0132,
             0x0110, 0x8115, 0x811f, 0x011a, 0x810b, 0x010e, 0x0104, 0x8101,
             0x8303, 0x0306, 0x030c, 0x8309, 0x0318, 0x831d, 0x8317, 0x0312,
             0x0330, 0x8335, 0x833f, 0x033a, 0x832b, 0x032e, 0x0324, 0x8321,
             0x0360, 0x8365, 0x836f, 0x036a, 0x837b, 0x037e, 0x0374, 0x8371,
             0x8353, 0x0356, 0x035c, 0x8359, 0x0348, 0x834d, 0x8347, 0x0342,
             0x03c0, 0x83c5, 0x83cf, 0x03ca, 0x83db, 0x03de, 0x03d4, 0x83d1,
             0x83f3, 0x03f6, 0x03fc, 0x83f9, 0x03e8, 0x83ed, 0x83e7, 0x03e2,
             0x83a3, 0x03a6, 0x03ac, 0x83a9, 0x03b8, 0x83bd, 0x83b7, 0x03b2,
             0x0390, 0x8395, 0x839f, 0x039a, 0x838b, 0x038e, 0x0384, 0x8381,
             0x0280, 0x8285, 0x828f, 0x028a, 0x829b, 0x029e, 0x0294, 0x8291,
             0x82b3, 0x02b6, 0x02bc, 0x82b9, 0x02a8, 0x82ad, 0x82a7, 0x02a2,
             0x82e3, 0x02e6, 0x02ec, 0x82e9, 0x02f8, 0x82fd, 0x82f7, 0x02f2,
             0x02d0, 0x82d5, 0x82df, 0x02da, 0x82cb, 0x02ce, 0x02c4, 0x82c1,
             0x8243, 0x0246, 0x024c, 0x8249, 0x0258, 0x825d, 0x8257, 0x0252,
             0x0270, 0x8275, 0x827f, 0x027a, 0x826b, 0x026e, 0x0264, 0x8261,
             0x0220, 0x8225, 0x822f, 0x022a, 0x823b, 0x023e, 0x0234, 0x8231,
             0x8213, 0x0216, 0x021c, 0x8219, 0x0208, 0x820d, 0x8207, 0x0202]

    def update(self, byte):
        self.value = ((self.TABLE[(self.value >> 8) ^ byte] ^
                       (self.value << 8)) & 0xFFFF)
