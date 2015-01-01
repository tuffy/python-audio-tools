#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from sys import version_info
from audiotools.bitstream import BitstreamWriter
from audiotools import BufferedPCMReader


if version_info[0] >= 3:
    def bytes_to_ints(b):
        return list(b)
else:
    def bytes_to_ints(b):
        return map(ord, b)


COMMAND_SIZE = 2
VERBATIM_SIZE = 5
VERBATIM_BYTE_SIZE = 8
ENERGY_SIZE = 3
BITSHIFT_SIZE = 2

(FN_DIFF0,
 FN_DIFF1,
 FN_DIFF2,
 FN_DIFF3,
 FN_QUIT,
 FN_BLOCKSIZE,
 FN_BITSHIFT,
 FN_QLPC,
 FN_ZERO,
 FN_VERBATIM) = range(10)


def encode_shn(filename,
               pcmreader,
               is_big_endian,
               signed_samples,
               header_data,
               footer_data=b"",
               block_size=256):
    """filename is a string to the output file's path
    pcmreader is a PCMReader object
    header_data and footer_data are binary strings
    block_size is the default size of each Shorten audio command
    """

    pcmreader = BufferedPCMReader(pcmreader)
    output_file = open(filename, "wb")
    writer = BitstreamWriter(output_file, False)

    left_shift = 0
    wrapped_channels = [[] for c in range(pcmreader.channels)]

    # write magic number and version
    writer.build("4b 8u", [b"ajkg", 2])

    bytes_written = __Counter__()
    writer.add_callback(bytes_written.byte)

    # write header from PCMReader info and encoding options
    if pcmreader.bits_per_sample == 8:
        if signed_samples:
            write_long(writer, 1)  # signed, 8-bit
            sign_adjustment = 0
        else:
            write_long(writer, 2)  # unsigned, 8-bit
            sign_adjustment = 1 << (pcmreader.bits_per_sample - 1)
        # 8-bit samples have no endianness
    elif pcmreader.bits_per_sample == 16:
        if signed_samples:
            if is_big_endian:
                write_long(writer, 3)  # signed, 16-bit, big-endian
            else:
                write_long(writer, 5)  # signed, 16-bit, little-endian
            sign_adjustment = 0
        else:
            if is_big_endian:
                write_long(writer, 4)  # unsigned, 16-bit, big-endian
            else:
                write_long(writer, 6)  # unsigned, 16-bit, little-endian
            sign_adjustment = 1 << (pcmreader.bits_per_sample - 1)
    else:
        raise ValueError("unsupported bits_per_sample")

    write_long(writer, pcmreader.channels)
    write_long(writer, block_size)
    write_long(writer, 0)  # max LPC
    write_long(writer, 0)  # mean count
    write_long(writer, 0)  # bytes to skip

    # write header as a VERBATIM block
    write_unsigned(writer, COMMAND_SIZE, FN_VERBATIM)
    write_unsigned(writer, VERBATIM_SIZE, len(header_data))
    for b in bytes_to_ints(header_data):
        write_unsigned(writer, VERBATIM_BYTE_SIZE, b)

    # split PCMReader into block_size chunks
    # and continue until the number of PCM frames is 0
    frame = pcmreader.read(block_size)
    while len(frame) > 0:
        # if the chunk isn't block_size frames long,
        # issue a command to change it
        if frame.frames != block_size:
            block_size = frame.frames
            write_unsigned(writer, COMMAND_SIZE, FN_BLOCKSIZE)
            write_long(writer, block_size)

        # split chunk into individual channels
        for c in range(pcmreader.channels):
            # convert PCM data to unsigned, if necessary
            if signed_samples:
                channel = list(frame.channel(c))
            else:
                channel = [s + sign_adjustment for s in frame.channel(c)]

            # if all samples are 0, issue a ZERO command
            if all_zeroes(channel):
                write_unsigned(writer, COMMAND_SIZE, FN_ZERO)

                # wrap zeroes around for next set of channels
                wrapped_channels[c] = channel
            else:
                # if channel's shifted bits have changed
                # from the previous channel's shift
                # issue a new BITSHIFT command
                wasted_bits = wasted_bps(channel)
                if wasted_bits != left_shift:
                    write_unsigned(writer, COMMAND_SIZE, FN_BITSHIFT)
                    write_unsigned(writer, BITSHIFT_SIZE, wasted_bits)
                    left_shift = wasted_bits

                # and shift the channel's bits if the amount is still > 0
                if left_shift > 0:
                    shifted = [s >> left_shift for s in channel]
                else:
                    shifted = channel

                # determine the best DIFF command and residuals
                # to issue for shifted channel data
                (diff, residuals) = best_diff(wrapped_channels[c], shifted)

                # determine the best energy size for DIFF's residuals
                energy = best_energy(residuals)

                # write DIFF command, energy size and residuals
                write_unsigned(writer, COMMAND_SIZE,
                               {1: FN_DIFF1,
                                2: FN_DIFF2,
                                3: FN_DIFF3}[diff])
                write_unsigned(writer, ENERGY_SIZE, energy)
                for residual in residuals:
                    write_signed(writer, energy, residual)

                # wrap shifted channels around for next set of channels
                wrapped_channels[c] = shifted

        # and get another set of channels to encode
        frame = pcmreader.read(block_size)

    # once all PCM data has been sent
    # if there's any footer data, write it as another VERBATIM block
    if len(footer_data) > 0:
        write_unsigned(writer, COMMAND_SIZE, FN_VERBATIM)
        write_unsigned(writer, VERBATIM_SIZE, len(footer_data))
        for b in bytes_to_ints(footer_data):
            write_unsigned(writer, VERBATIM_BYTE_SIZE, b)

    # issue a QUIT command
    write_unsigned(writer, COMMAND_SIZE, FN_QUIT)

    # finally, due to Shorten's silly way of using bit buffers,
    # output (not counting the 5 bytes of magic + version)
    # must be padded to a multiple of 4 bytes
    # or its reference decoder explodes
    writer.byte_align()
    while (int(bytes_written) % 4) != 0:
        writer.write(8, 0)
    writer.close()


def write_unsigned(writer, size, value):
    assert(value >= 0)
    MSB = value >> size
    LSB = value - (MSB << size)
    writer.unary(1, MSB)
    writer.write(size, LSB)


def write_signed(writer, size, value):
    if value >= 0:
        write_unsigned(writer, size + 1, value * 2)
    else:
        write_unsigned(writer, size + 1, ((-value - 1) * 2) + 1)


def write_long(writer, value):
    assert(value >= 0)
    from math import log

    if value == 0:
        write_unsigned(writer, 2, 0)
        write_unsigned(writer, 0, 0)
    else:
        lsb_size = int(log(value) / log(2)) + 1
        write_unsigned(writer, 2, lsb_size)
        write_unsigned(writer, lsb_size, value)


def best_diff(previous_samples, samples):
    """given a list of previous samples (which may be empty)
    and a list of samples for a given channel
    returns (diff, residuals) where diff is 1, 2 or 3
    and residuals is a list of residual values for that channel"""

    # build a full list of samples containing at least 3 previous samples
    # which are padded with 0s if there aren't enough present
    if len(previous_samples) < 3:
        full_samples = ([0] * (3 - len(previous_samples)) +
                        previous_samples + samples)
    else:
        full_samples = previous_samples[-3:] + samples

    # determine delta1 from the samples list
    delta1 = [n - p for (p, n) in zip(full_samples, full_samples[1:])]
    abs_sum1 = sum(map(abs, delta1[2:]))
    assert(len(delta1) == len(samples) + 2)

    # determine delta2 from delta1
    delta2 = [n - p for (p, n) in zip(delta1, delta1[1:])]
    abs_sum2 = sum(map(abs, delta2[1:]))
    assert(len(delta2) == len(samples) + 1)

    # determine delta3 from delta2
    delta3 = [n - p for (p, n) in zip(delta2, delta2[1:])]
    abs_sum3 = sum(map(abs, delta3))
    assert(len(delta3) == len(samples))

    # pick DIFF command based on minimum abs sum
    # and return residuals
    if abs_sum1 < min(abs_sum2, abs_sum3):
        return (1, delta1[2:])
    elif abs_sum2 < abs_sum3:
        return (2, delta2[1:])
    else:
        return (3, delta3)


def best_energy(residuals):
    """given a list of residuals, returns the best energy size
    as an unsigned int"""

    partition_sum = sum(map(abs, residuals))
    rice_parameter = 0
    while (len(residuals) * (2 ** rice_parameter)) < partition_sum:
        rice_parameter += 1

    return rice_parameter


def all_zeroes(samples):
    for s in samples:
        if s != 0:
            return False
    else:
        return True


def wasted_bps(samples):
    def wasted_bits(s):
        w = 0
        while (s & 1) == 0:
            w += 1
            s >>= 1
        return w

    wasted = 2 ** 32
    for s in samples:
        if s != 0:
            wasted = min(wasted_bits(s), wasted)
            if wasted == 0:
                return 0

    # all samples are 0
    if wasted == 2 ** 32:
        return 0
    else:
        return wasted


class __Counter__(object):
    def __init__(self):
        self.value = 0

    def byte(self, b):
        self.value += 1

    def __int__(self):
        return self.value
