#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2014  Brian Langenberger

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

from audiotools.bitstream import BitstreamReader
from audiotools.pcm import empty_framelist, from_list
from hashlib import md5


class FlacDecoder(object):
    CHANNEL_COUNT = [1, 2, 3, 4, 5, 6, 7, 8, 2, 2, 2,
                     None, None, None, None, None]

    (SUBFRAME_CONSTANT,
     SUBFRAME_VERBATIM,
     SUBFRAME_FIXED,
     SUBFRAME_LPC) = range(4)

    def __init__(self, filename, channel_mask):
        self.reader = BitstreamReader(open(filename, "rb"), False)

        if (self.reader.read_bytes(4) != b'fLaC'):
            raise ValueError("invalid FLAC file")

        self.current_md5sum = md5()

        # locate the STREAMINFO,
        # which is sometimes needed to handle non-subset streams
        for (block_id,
             block_size,
             block_reader) in self.metadata_blocks(self.reader):
            if (block_id == 0):
                # read STREAMINFO
                self.minimum_block_size = block_reader.read(16)
                self.maximum_block_size = block_reader.read(16)
                self.minimum_frame_size = block_reader.read(24)
                self.maximum_frame_size = block_reader.read(24)
                self.sample_rate = block_reader.read(20)
                self.channels = block_reader.read(3) + 1
                self.channel_mask = channel_mask
                self.bits_per_sample = block_reader.read(5) + 1
                self.total_frames = block_reader.read(36)
                self.md5sum = block_reader.read_bytes(16)

                # these are frame header lookup tables
                # which vary slightly depending on STREAMINFO's values
                self.BLOCK_SIZE = [self.maximum_block_size,
                                   192,  576,  1152,
                                   2304, 4608,  None,  None,
                                   256,  512,  1024,  2048,
                                   4096, 8192, 16384, 32768]
                self.SAMPLE_RATE = [self.sample_rate,
                                    88200, 176400, 192000,
                                    8000,  16000,  22050, 24000,
                                    32000,  44100,  48000, 96000,
                                    None,   None,   None,  None]
                self.BITS_PER_SAMPLE = [self.bits_per_sample,
                                        8, 12, None, 16, 20, 24, None]

    def metadata_blocks(self, reader):
        """yields a (block_id, block_size, block_reader) tuple
        per metadata block where block_reader is a BitstreamReader substream"""

        (last_block, block_id, block_size) = self.reader.parse("1u 7u 24u")
        while (last_block == 0):
            yield (block_id, block_size, self.reader.substream(block_size))
            (last_block, block_id, block_size) = self.reader.parse("1u 7u 24u")
        else:
            yield (block_id, block_size, self.reader.substream(block_size))

    def read(self, pcm_frames):
        # if the stream is exhausted,
        # verify its MD5 sum and return an empty pcm.FrameList object
        if (self.total_frames < 1):
            if (self.md5sum == self.current_md5sum.digest()):
                return empty_framelist(self.channels, self.bits_per_sample)
            else:
                raise ValueError("MD5 checksum mismatch")

        crc16 = CRC16()
        self.reader.add_callback(crc16.update)

        # fetch the decoding parameters from the frame header
        (block_size,
         channel_assignment,
         bits_per_sample) = self.read_frame_header()
        channel_count = self.CHANNEL_COUNT[channel_assignment]
        if (channel_count is None):
            raise ValueError("invalid channel assignment")

        # channel data will be a list of signed sample lists, one per channel
        # such as  [[1, 2, 3, ...], [4, 5, 6, ...]]  for a 2 channel stream
        channel_data = []

        for channel_number in range(channel_count):
            if ((channel_assignment == 0x8) and (channel_number == 1)):
                # for left-difference assignment
                # the difference channel has 1 additional bit
                channel_data.append(self.read_subframe(block_size,
                                                       bits_per_sample + 1))
            elif ((channel_assignment == 0x9) and (channel_number == 0)):
                # for difference-right assignment
                # the difference channel has 1 additional bit
                channel_data.append(self.read_subframe(block_size,
                                                       bits_per_sample + 1))
            elif ((channel_assignment == 0xA) and (channel_number == 1)):
                # for average-difference assignment
                # the difference channel has 1 additional bit
                channel_data.append(self.read_subframe(block_size,
                                                       bits_per_sample + 1))
            else:
                # otherwise, use the frame's bits-per-sample value
                channel_data.append(self.read_subframe(block_size,
                                                       bits_per_sample))

        # one all the subframes have been decoded,
        # reconstruct them depending on the channel assignment
        if (channel_assignment == 0x8):
            # left-difference
            samples = []
            for (left, difference) in zip(*channel_data):
                samples.append(left)
                samples.append(left - difference)
        elif (channel_assignment == 0x9):
            # difference-right
            samples = []
            for (difference, right) in zip(*channel_data):
                samples.append(difference + right)
                samples.append(right)
        elif (channel_assignment == 0xA):
            # mid-side
            samples = []
            for (mid, side) in zip(*channel_data):
                samples.append((((mid * 2) + (side % 2)) + side) // 2)
                samples.append((((mid * 2) + (side % 2)) - side) // 2)
        else:
            # independent
            samples = [0] * block_size * channel_count
            for (i, channel) in enumerate(channel_data):
                samples[i::channel_count] = channel

        self.reader.byte_align()

        # read and verify the frame's trailing CRC-16 footer
        self.reader.read(16)
        self.reader.pop_callback()
        if (int(crc16) != 0):
            raise ValueError("CRC16 mismatch in frame footer")

        # deduct the amount of PCM frames from the remaining amount
        self.total_frames -= block_size

        # build a pcm.FrameList object from the combined samples
        framelist = from_list(samples, channel_count, bits_per_sample, True)

        # update the running MD5 sum calculation with the frame's data
        self.current_md5sum.update(framelist.to_bytes(0, 1))

        # and finally return the frame data
        return framelist

    def read_frame_header(self):
        crc8 = CRC8()
        self.reader.add_callback(crc8.update)

        # read the 32-bit FLAC frame header
        sync_code = self.reader.read(14)
        if (sync_code != 0x3FFE):
            raise ValueError("invalid sync code")

        self.reader.skip(1)
        blocking_strategy = self.reader.read(1)
        block_size_bits = self.reader.read(4)
        sample_rate_bits = self.reader.read(4)
        channel_assignment = self.reader.read(4)
        bits_per_sample_bits = self.reader.read(3)
        self.reader.skip(1)

        # the frame number is a UTF-8 encoded value
        # which takes a variable number of whole bytes
        frame_number = self.read_utf8()

        # unpack the 4 bit block size field
        # which is the total PCM frames in the FLAC frame
        # and may require up to 16 more bits if the frame is usually-sized
        # (which typically happens at the end of the stream)
        if (block_size_bits == 0x6):
            block_size = self.reader.read(8) + 1
        elif (block_size_bits == 0x7):
            block_size = self.reader.read(16) + 1
        else:
            block_size = self.BLOCK_SIZE[block_size_bits]

        # unpack the 4 bit sample rate field
        # which is used for playback, but not needed for decoding
        # and may require up to 16 more bits
        # if the stream has a particularly unusual sample rate
        if (sample_rate_bits == 0xC):
            sample_rate = self.reader.read(8) * 1000
        elif (sample_rate_bits == 0xD):
            sample_rate = self.reader.read(16)
        elif (sample_rate_bits == 0xE):
            sample_rate = self.reader.read(16) * 10
        elif (sample_rate_bits == 0xF):
            raise ValueError("invalid sample rate")
        else:
            sample_rate = self.SAMPLE_RATE[sample_rate_bits]

        # unpack the 3 bit bits-per-sample field
        # this never requires additional bits
        if ((bits_per_sample_bits == 0x3) or (bits_per_sample_bits == 0x7)):
            raise ValueError("invalid bits per sample")
        else:
            bits_per_sample = self.BITS_PER_SAMPLE[bits_per_sample_bits]

        # read and verify frame's CRC-8 value
        self.reader.read(8)
        self.reader.pop_callback()
        if (int(crc8) != 0):
            raise ValueError("CRC8 mismatch in frame header")

        return (block_size, channel_assignment, bits_per_sample)

    def read_subframe_header(self):
        """returns a tuple of (subframe_type, subframe_order, wasted_bps)"""

        self.reader.skip(1)
        subframe_type = self.reader.read(6)
        if (self.reader.read(1) == 1):
            wasted_bps = self.reader.unary(1) + 1
        else:
            wasted_bps = 0

        # extract "order" value from 6 bit subframe type, if necessary
        if (subframe_type == 0):
            return (self.SUBFRAME_CONSTANT, None, wasted_bps)
        elif (subframe_type == 1):
            return (self.SUBFRAME_VERBATIM, None, wasted_bps)
        elif ((subframe_type & 0x38) == 0x08):
            return (self.SUBFRAME_FIXED, subframe_type & 0x07, wasted_bps)
        elif ((subframe_type & 0x20) == 0x20):
            return (self.SUBFRAME_LPC, (subframe_type & 0x1F) + 1, wasted_bps)
        else:
            raise ValueError("invalid subframe type")

    def read_subframe(self, block_size, bits_per_sample):
        (subframe_type,
         subframe_order,
         wasted_bps) = self.read_subframe_header()

        # read a list of signed sample values
        # depending on the subframe type, block size,
        # adjusted bits per sample and optional subframe order
        if (subframe_type == self.SUBFRAME_CONSTANT):
            subframe_samples = self.read_constant_subframe(
                block_size, bits_per_sample - wasted_bps)
        elif (subframe_type == self.SUBFRAME_VERBATIM):
            subframe_samples = self.read_verbatim_subframe(
                block_size, bits_per_sample - wasted_bps)
        elif (subframe_type == self.SUBFRAME_FIXED):
            subframe_samples = self.read_fixed_subframe(
                block_size, bits_per_sample - wasted_bps, subframe_order)
        else:
            subframe_samples = self.read_lpc_subframe(
                block_size, bits_per_sample - wasted_bps, subframe_order)

        # account for wasted bits-per-sample, if necessary
        if (wasted_bps):
            return [sample << wasted_bps for sample in subframe_samples]
        else:
            return subframe_samples

    def read_constant_subframe(self, block_size, bits_per_sample):
        sample = self.reader.read_signed(bits_per_sample)
        return [sample] * block_size

    def read_verbatim_subframe(self, block_size, bits_per_sample):
        return [self.reader.read_signed(bits_per_sample)
                for x in range(block_size)]

    def read_fixed_subframe(self, block_size, bits_per_sample, order):
        # "order" number of warm-up samples
        samples = [self.reader.read_signed(bits_per_sample)
                   for i in range(order)]

        # "block_size" - "order" number of residual values
        residuals = self.read_residual(block_size, order)

        # which are applied to the warm-up samples
        # depending on the FIXED subframe order
        # and results in "block_size" number of total samples
        if (order == 0):
            return residuals
        elif (order == 1):
            for residual in residuals:
                samples.append(samples[-1] +
                               residual)
            return samples
        elif (order == 2):
            for residual in residuals:
                samples.append((2 * samples[-1]) -
                               samples[-2] +
                               residual)
            return samples
        elif (order == 3):
            for residual in residuals:
                samples.append((3 * samples[-1]) -
                               (3 * samples[-2]) +
                               samples[-3] +
                               residual)
            return samples
        elif (order == 4):
            for residual in residuals:
                samples.append((4 * samples[-1]) -
                               (6 * samples[-2]) +
                               (4 * samples[-3]) -
                               samples[-4] +
                               residual)
            return samples
        else:
            raise ValueError("unsupported FIXED subframe order")

    def read_lpc_subframe(self, block_size, bits_per_sample, order):
        # "order" number of warm-up samples
        samples = [self.reader.read_signed(bits_per_sample)
                   for i in range(order)]

        # the size of each QLP coefficient, in bits
        qlp_precision = self.reader.read(4)

        # the amount of right shift to apply
        # during LPC calculation
        # (though this is a signed value, negative shifts are noops
        # in the reference FLAC decoder)
        qlp_shift_needed = max(self.reader.read_signed(5), 0)

        # "order" number of signed QLP coefficients
        qlp_coeffs = [self.reader.read_signed(qlp_precision + 1)
                      for i in range(order)]
        # QLP coefficients are applied in reverse order
        qlp_coeffs.reverse()

        # "block_size" - "order" number of residual values
        residuals = self.read_residual(block_size, order)

        # which are applied to the running LPC calculation
        for residual in residuals:
            samples.append((sum([coeff * sample for (coeff, sample) in
                                 zip(qlp_coeffs, samples[-order:])]) >>
                            qlp_shift_needed) + residual)

        return samples

    def read_residual(self, block_size, order):
        residuals = []

        coding_method = self.reader.read(2)
        partition_order = self.reader.read(4)

        # each parititon contains  block_size / 2 ** partition_order
        # number of residuals
        for partition_number in range(2 ** partition_order):
            if (partition_number == 0):
                # except for the first partition
                # which contains "order" less than the rest
                residuals.extend(
                    self.read_residual_partition(
                        coding_method,
                        (block_size // 2 ** partition_order) - order))
            else:
                residuals.extend(
                    self.read_residual_partition(
                        coding_method,
                        block_size // 2 ** partition_order))

        return residuals

    def read_residual_partition(self, coding_method, residual_count):
        if (coding_method == 0):
            # the Rice parameters determines the number of
            # least-significant bits to read for each residual
            rice_parameter = self.reader.read(4)
            if (rice_parameter == 0xF):
                escape_code = self.reader.read(5)
                return [self.reader.read_signed(escape_code)
                        for i in range(residual_count)]
        elif (coding_method == 1):
            # 24 bps streams may use a 5-bit Rice parameter
            # for better compression
            rice_parameter = self.reader.read(5)
            if (rice_parameter == 0x1F):
                escape_code = self.reader.read(5)
                return [self.reader.read_signed(escape_code)
                        for i in range(residual_count)]
        else:
            raise ValueError("invalid Rice coding parameter")

        # a list of signed residual values
        partition_residuals = []

        for i in range(residual_count):
            msb = self.reader.unary(1)              # most-significant bits
            lsb = self.reader.read(rice_parameter)  # least-significant bits
            value = (msb << rice_parameter) | lsb   # combined into a value
            if (value & 1):   # whose least-significant bit is the sign value
                partition_residuals.append(-(value >> 1) - 1)
            else:
                partition_residuals.append(value >> 1)

        return partition_residuals

    def read_utf8(self):
        total_bytes = self.reader.unary(0)
        value = self.reader.read(7 - total_bytes)
        while (total_bytes > 1):
            value = ((value << 6) | self.reader.parse("2p 6u")[0])
            total_bytes -= 1
        return value

    def close(self):
        self.reader.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class CRC8(object):
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
