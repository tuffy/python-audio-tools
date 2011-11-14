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

from audiotools.bitstream import BitstreamWriter
from audiotools.bitstream import BitstreamRecorder
from audiotools.bitstream import BitstreamAccumulator
from audiotools import BufferedPCMReader

class Encoding_Options:
    def __init__(self, block_size,
                 initial_history, history_multiplier, maximum_K,
                 interlacing_shift,
                 min_interlacing_leftweight, max_interlacing_leftweight):
        self.block_size = block_size
        self.initial_history = initial_history
        self.history_multiplier = history_multiplier
        self.maximum_K = maximum_K
        self.interlacing_shift = interlacing_shift
        self.min_interlacing_leftweight = min_interlacing_leftweight
        self.max_interlacing_leftweight = max_interlacing_leftweight


QLP_SHIFT_NEEDED = 9


class ByteCounter:
    def __init__(self):
        self.count = 0

    def update(self, b):
        self.count += 1

    def __int__(self):
        return self.count


def encode_mdat(file, pcmreader,
                block_size=4096,
                initial_history=10,
                history_multiplier=40,
                maximum_K=14,
                interlacing_shift=2,
                min_interlacing_leftweight=0,
                max_interlacing_leftweight=4):

    options = Encoding_Options(block_size,
                               initial_history,
                               history_multiplier,
                               maximum_K,
                               interlacing_shift,
                               min_interlacing_leftweight,
                               max_interlacing_leftweight)

    pcmreader = BufferedPCMReader(pcmreader)

    mdat = BitstreamWriter(file, 0)
    mdat_length = ByteCounter()
    mdat.add_callback(mdat_length.update)

    frame_sample_sizes = []
    frame_byte_sizes = []
    frame_file_offsets = []

    #write placeholder mdat header
    mdat.write(32, 0)
    mdat.write_bytes("mdat")

    #read FrameList objects until stream is empty
    frame = pcmreader.read(block_size *
                           pcmreader.channels *
                           (pcmreader.bits_per_sample / 8))
    while (len(frame) > 0):
        frame_sample_sizes.append(frame.frames)
        frame_file_offsets.append(int(mdat_length))
        encode_frameset(mdat, pcmreader, options, frame)
        frame_byte_sizes.append(int(mdat_length) - frame_file_offsets[-1])
        frame = pcmreader.read(block_size *
                               pcmreader.channels *
                               (pcmreader.bits_per_sample / 8))

    #finally, return to start of mdat and write actual length
    mdat.byte_align()
    mdat.pop_callback()
    file.seek(0, 0)
    mdat.write(32, int(mdat_length))

    return (frame_sample_sizes,
            frame_byte_sizes,
            frame_file_offsets,
            int(mdat_length))


def encode_frameset(writer, pcmreader, options, frame):
    if (pcmreader.channels == 1):
        encode_frame(writer, pcmreader, options, [frame.channel(0)])
    elif (pcmreader.channels == 2):
        encode_frame(writer, pcmreader, options, [frame.channel(0),
                                                  frame.channel(1)])
    else:
        raise NotImplementedError()

    writer.write(3, 7)
    writer.byte_align()


def encode_frame(writer, pcmreader, options, channels):
    assert(len(channels) > 0)

    uncompressed_frame = BitstreamRecorder(0)
    compressed_frame = BitstreamRecorder(0)

    writer.write(3, len(channels) - 1)

    encode_uncompressed_frame(uncompressed_frame,
                              pcmreader,
                              options,
                              channels)

    if (len(channels[0]) >= 10):
        try:
            encode_compressed_frame(compressed_frame,
                                    pcmreader,
                                    options,
                                    channels)

            if (compressed_frame.bits() < uncompressed_frame.bits()):
                compressed_frame.copy(writer)
            else:
                uncompressed_frame.copy(writer)
        except ResidualOverflow:
            uncompressed_frame.copy(writer)
    else:
        uncompressed_frame.copy(writer)


def encode_uncompressed_frame(writer, pcmreader, options, channels):
    writer.write(16, 0)                           #unusued
    if (len(channels[0]) == options.block_size):  #has block size
        writer.write(1, 0)
    else:
        writer.write(1, 1)
    writer.write(2, 0)                            #no uncompressed LSBs
    writer.write(1, 1)                            #not compressed
    if (len(channels[0]) != options.block_size):  #block size
        writer.write(32, len(channels[0]))

    #write out uncompressed samples
    for pcm_frame in zip(*channels):
        for sample in pcm_frame:
            writer.write_signed(pcmreader.bits_per_sample, sample)


class ResidualOverflow(Exception):
    pass


def encode_compressed_frame(writer, pcmreader, options, channels):
    if (pcmreader.bits_per_sample <= 16):
        uncompressed_LSBs = 0
        LSBs = []
    else:
        #extract uncompressed LSBs
        uncompressed_LSBs = (pcmreader.bits_per_sample - 16) / 8
        LSBs = []
        for i in xrange(len(channels[0])):
            for c in xrange(len(channels)):
                LSBs.append(channels[c][i] %
                            (2 ** (pcmreader.bits_per_sample - 16)))
                channels[c][i] >>= (pcmreader.bits_per_sample - 16)

    if (len(channels) == 1):
        encode_non_interlaced_frame(writer,
                                    pcmreader,
                                    options,
                                    uncompressed_LSBs,
                                    LSBs,
                                    channels)
    else:
        interlaced_frames = [BitstreamRecorder(0) for i in
                             xrange(options.min_interlacing_leftweight,
                                    options.max_interlacing_leftweight + 1)]
        for (leftweight,
             frame) in zip(xrange(options.min_interlacing_leftweight,
                                  options.max_interlacing_leftweight + 1),
                           interlaced_frames):
            encode_interlaced_frame(frame,
                                    pcmreader,
                                    options,
                                    uncompressed_LSBs,
                                    LSBs,
                                    options.interlacing_shift,
                                    leftweight,
                                    channels)

        for i in xrange(len(interlaced_frames) - 1):
            if (interlaced_frames[i].bits() <
                min([f.bits() for f in interlaced_frames[i + 1:]])):
                interlaced_frames[i].copy(writer)


def encode_non_interlaced_frame(writer, pcmreader, options,
                                uncompressed_LSBs, LSBs, channels):
    assert(len(channels) == 1)

    writer.write(16, 0)                           #unused
    if (len(channels[0]) != options.block_size):  #has block size
        writer.write(1, 1)
    else:
        writer.write(1, 0)
    writer.write(2, uncompressed_LSBs)            #uncompressed LSBs
    writer.write(1, 0)                            #is compressed
    if (len(channels[0]) != options.block_size):  #block size
        writer.write(32, len(channels[0]))
    writer.write(8, 0)                            #interlacing shift
    writer.write(8, 0)                            #interlacing leftweight

    sample_size = pcmreader.bits_per_sample - (uncompressed_LSBs * 8)

    (LPC_coefficients, residual) = calculate_lpc_coefficients(pcmreader,
                                                              options,
                                                              sample_size,
                                                              channels[0])
    write_subframe_header(writer, LPC_coefficients)
    if (uncompressed_LSBs > 0):
        for LSB in LSBs:
            writer.write(uncompressed_LSBs * 8, LSB)
    residual.copy(writer)


def encode_interlaced_frame(writer, pcmreader, options,
                            uncompressed_LSBs, LSBs,
                            interlacing_shift, interlacing_leftweight,
                            channels):
    assert(len(channels) == 2)

    writer.write(16, 0)                           #unused
    if (len(channels[0]) != options.block_size):  #has block size
        writer.write(1, 1)
    else:
        writer.write(1, 0)
    writer.write(2, uncompressed_LSBs)            #uncompressed LSBs
    writer.write(1, 0)                            #is compressed
    if (len(channels[0]) != options.block_size):  #block size
        writer.write(32, len(channels[0]))
    writer.write(8, interlacing_shift)
    writer.write(8, interlacing_leftweight)

    sample_size = pcmreader.bits_per_sample - (uncompressed_LSBs * 8) + 1

    (correlated0,
     correlated1) = correlate_channels(channels[0],
                                       channels[1],
                                       interlacing_shift,
                                       interlacing_leftweight)

    (LPC_coefficients0, residual0) = calculate_lpc_coefficients(pcmreader,
                                                                options,
                                                                sample_size,
                                                                correlated0)

    (LPC_coefficients1, residual1) = calculate_lpc_coefficients(pcmreader,
                                                                options,
                                                                sample_size,
                                                                correlated1)

    write_subframe_header(writer, LPC_coefficients0)
    write_subframe_header(writer, LPC_coefficients1)
    if (uncompressed_LSBs > 0):
        for LSB in LSBs:
            writer.write(uncompressed_LSBs * 8, LSB)
    residual0.copy(writer)
    residual1.copy(writer)


def correlate_channels(channel0, channel1,
                       interlacing_shift, interlacing_leftweight):
    assert(len(channel0) == len(channel1))

    if (interlacing_leftweight > 0):
        correlated0 = []
        correlated1 = []
        for i in xrange(len(channel0)):
            correlated0.append(channel1[i] +
                               (((channel0[i] - channel1[i]) *
                                 interlacing_leftweight) >> interlacing_shift))
            correlated1.append(channel0[i] - channel1[i])

        return (correlated0, correlated1)
    else:
        return (list(channel0), list(channel1))


def calculate_lpc_coefficients(pcmreader, options, sample_size, channel):
    windowed = [s * t for s,t in zip(channel,
                                     tukey_window(len(channel), 0.5))]

    autocorrelated = [sum([s1 * s2 for s1,s2 in zip(windowed,
                                                    windowed[lag:])])
                        for lag in xrange(0,9)]

    assert(len(autocorrelated) == 9)

    lp_coefficients = compute_lp_coefficients(autocorrelated)

    assert(len(lp_coefficients) == 8)

    qlp_coefficients4 = quantize_coefficients(lp_coefficients, 4)
    qlp_coefficients8 = quantize_coefficients(lp_coefficients, 8)

    residuals4 = compute_residuals(qlp_coefficients4[:], channel)
    residuals8 = compute_residuals(qlp_coefficients8[:], channel)

    residual_block4 = BitstreamRecorder(0)
    residual_block8 = BitstreamRecorder(0)

    encode_residuals(residual_block4, options, sample_size, residuals4)
    encode_residuals(residual_block8, options, sample_size, residuals8)

    if (residual_block4.bits() < residual_block8.bits()):
        return (qlp_coefficients4, residual_block4)
    else:
        return (qlp_coefficients8, residual_block8)


def tukey_window(sample_count, alpha):
    from math import cos,pi

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


def compute_lp_coefficients(autocorrelation):
    maximum_lpc_order = len(autocorrelation) - 1

    k0 = autocorrelation[1] / autocorrelation[0]
    lp_coefficients = [[k0]]
    error = [autocorrelation[0] * (1 - k0 ** 2)]

    for i in xrange(1, maximum_lpc_order):
        ki = (autocorrelation[i + 1] -
              sum([x * y for (x,y) in
                   zip(lp_coefficients[i - 1],
                       reversed(autocorrelation[1:i + 1]))])) / error[i - 1]

        lp_coefficients.append([c1 - (ki * c2) for (c1,c2) in
                                zip(lp_coefficients[i - 1],
                                   reversed(lp_coefficients[i - 1]))] + [ki])

        error.append(error[i - 1] * (1 - ki ** 2))

    return lp_coefficients


def quantize_coefficients(lp_coefficients, order):
    qlp_max = 2 ** 15 - 1
    qlp_min = -(2 ** 15)
    error = 0.0
    qlp_coeffs = []

    for (i,lp_coeff) in enumerate(lp_coefficients[order - 1]):
        error += (lp_coeff * 2 ** 9)
        qlp_coeffs.append(min(max(int(round(error)), qlp_min), qlp_max))
        error -= qlp_coeffs[-1]

    return qlp_coeffs


def compute_residuals(qlp_coefficients, channel):
    def SIGN(x):
        if (x > 0):
            return 1
        elif (x == 0):
            return 0
        else:
            return -1

    channel = list(channel)

    residuals = [channel[0]]
    for i in xrange(1, len(qlp_coefficients) + 1):
        residuals.append(channel[i] - channel[i - 1])

    for i in xrange(len(qlp_coefficients) + 1, len(channel)):
        base_sample = channel[i - len(qlp_coefficients) - 1]

        lpc_sum = sum([(c * (s - base_sample)) for (c,s) in
                       zip(qlp_coefficients,
                           reversed(channel[i - len(qlp_coefficients):i]))])

        residual = (channel[i] -
                    (((lpc_sum + (1 << (QLP_SHIFT_NEEDED - 1))) >>
                      QLP_SHIFT_NEEDED) + base_sample))

        residuals.append(residual)

        if (residual > 0):
            for j in xrange(len(qlp_coefficients)):
                diff = base_sample - channel[i - len(qlp_coefficients) + j]
                sign = SIGN(diff)
                qlp_coefficients[len(qlp_coefficients) - j - 1] -= sign
                residual -= ((diff * sign) >> QLP_SHIFT_NEEDED) * (j + 1)
                if (residual <= 0):
                    break
        elif (residual < 0):
            for j in xrange(len(qlp_coefficients)):
                diff = base_sample - channel[i - len(qlp_coefficients) + j]
                sign = SIGN(diff)
                qlp_coefficients[len(qlp_coefficients) - j - 1] += sign
                residual -= ((diff * -sign) >> QLP_SHIFT_NEEDED) * (j + 1)
                if (residual >= 0):
                    break

    return residuals


def encode_residuals(writer, options, sample_size, residuals):
    def LOG2(v):
        #a slow version
        from math import log

        return int(log(v) / log(2))

    history = options.initial_history
    sign_modifier = 0

    i = 0
    while (i < len(residuals)):
        if (residuals[i] >= 0):
            unsigned = residuals[i] * 2;
        else:
            unsigned = (-residuals[i] * 2) - 1;

        if (unsigned >= 2 ** sample_size):
            raise ResidualOverflow()

        k = min(LOG2((history / 2 ** 9) + 3), options.maximum_K)

        encode_residual(writer, unsigned - sign_modifier, k, sample_size)

        sign_modifier = 0

        if (unsigned < 65535):
            history += ((unsigned * options.history_multiplier) -
                        ((history * options.history_multiplier) / 2 ** 9))
            i += 1
            if ((history < 128) and (i < len(residuals))):
                k = min(7 - LOG2(history) + ((history + 16) / 2 ** 6),
                        options.maximum_K)
                zeroes = 0
                while ((i < len(residuals)) and (residuals[i] == 0)):
                    zeroes += 1
                    i += 1
                encode_residual(writer, zeroes, k, 16)
                if (zeroes < 65535):
                    sign_modifier = 1
                history = 0
        else:
            i += 1
            history = 65535


def encode_residual(writer, unsigned, k, sample_size):
    MSB = unsigned / ((2 ** k) - 1)
    LSB = unsigned % ((2 ** k) - 1)

    if (MSB > 8):
        writer.write(9, 0x1FF)
        writer.write(sample_size, unsigned)
    else:
        writer.unary(0, MSB)
        if (k > 1):
            if (LSB > 0):
                writer.write(k, LSB + 1)
            else:
                writer.write(k - 1, 0)


def write_subframe_header(writer, QLP_coefficients):
    writer.write(4, 0)                     #prediction type
    writer.write(4, QLP_SHIFT_NEEDED)
    writer.write(3, 4)                     #Rice modifier
    writer.write(5, len(QLP_coefficients)) #coeff count
    for coeff in QLP_coefficients:
        writer.write_signed(16, coeff)
