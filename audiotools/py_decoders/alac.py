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

from audiotools import iter_last
from audiotools.bitstream import BitstreamReader
from audiotools.pcm import from_list, from_channels
from operator import concat


def log2(i):
    bits = -1
    while (i):
        bits += 1
        i >>= 1
    return bits


def sign_only(value):
    if (value == 0):
        return 0
    elif (value > 0):
        return 1
    else:
        return -1


def truncate_bits(value, bits):
    #truncate value to the given number of bits
    truncated = value & ((1 << bits) - 1)

    #apply newly created sign bit
    if (truncated & (1 << (bits - 1))):
        return truncated - (1 << bits)
    else:
        return truncated


class ALACDecoder:
    def __init__(self, filename):
        self.reader = BitstreamReader(open(filename, "rb"), 0)

        self.reader.mark()
        try:
            #locate the "alac" atom
            #which is full of required decoding parameters
            try:
                stsd = self.find_sub_atom("moov", "trak", "mdia",
                                          "minf", "stbl", "stsd")
            except KeyError:
                raise ValueError("required stsd atom not found")

            (stsd_version, descriptions) = stsd.parse("8u 24p 32u")
            (alac1,
             alac2,
             self.samples_per_frame,
             self.bits_per_sample,
             self.history_multiplier,
             self.initial_history,
             self.maximum_k,
             self.channels,
             self.sample_rate) = stsd.parse(
                #ignore much of the stuff in the "high" ALAC atom
                "32p 4b 6P 16p 16p 16p 4P 16p 16p 16p 16p 4P" +
                #and use the attributes in the "low" ALAC atom instead
                "32p 4b 4P 32u 8p 8u 8u 8u 8u 8u 16p 32p 32p 32u")

            self.channel_mask = {1: 0x0004,
                                 2: 0x0003,
                                 3: 0x0007,
                                 4: 0x0107,
                                 5: 0x0037,
                                 6: 0x003F,
                                 7: 0x013F,
                                 8: 0x00FF}.get(self.channels, 0)

            if ((alac1 != 'alac') or (alac2 != 'alac')):
                raise ValueError("Invalid alac atom")

            #also locate the "mdhd" atom
            #which contains the stream's length in PCM frames
            self.reader.rewind()
            mdhd = self.find_sub_atom("moov", "trak", "mdia", "mdhd")
            (version, ) = mdhd.parse("8u 24p")
            if (version == 0):
                (self.total_pcm_frames,) = mdhd.parse(
                    "32p 32p 32p 32u 2P 16p")
            elif (version == 1):
                (self.total_pcm_frames,) = mdhd.parse(
                    "64p 64p 32p 64U 2P 16p")
            else:
                raise ValueError("invalid mdhd version")

            #finally, set our stream to the "mdat" atom
            self.reader.rewind()
            (atom_size, atom_name) = self.reader.parse("32u 4b")
            while (atom_name != "mdat"):
                self.reader.skip_bytes(atom_size - 8)
                (atom_size, atom_name) = self.reader.parse("32u 4b")

        finally:
            self.reader.unmark()

    def find_sub_atom(self, *atom_names):
        reader = self.reader

        for (last, next_atom) in iter_last(iter(atom_names)):
            try:
                (length, stream_atom) = reader.parse("32u 4b")
                while (stream_atom != next_atom):
                    reader.skip_bytes(length - 8)
                    (length, stream_atom) = reader.parse("32u 4b")
                if (last):
                    return reader.substream(length - 8)
                else:
                    reader = reader.substream(length - 8)
            except IOError:
                raise KeyError(next_atom)

    def read(self, pcm_frames):
        #if the stream is exhausted, return an empty pcm.FrameList object
        if (self.total_pcm_frames == 0):
            return from_list([], self.channels, self.bits_per_sample, True)

        #otherwise, read one ALAC frameset's worth of frame data
        frameset_data = []
        frame_channels = self.reader.read(3) + 1
        while (frame_channels != 0x8):
            frameset_data.extend(self.read_frame(frame_channels))
            frame_channels = self.reader.read(3) + 1
        self.reader.byte_align()

        #reorder the frameset to Wave order, depending on channel count
        if ((self.channels == 1) or (self.channels == 2)):
            pass
        elif (self.channels == 3):
            frameset_data = [frameset_data[1],
                             frameset_data[2],
                             frameset_data[0]]
        elif (self.channels == 4):
            frameset_data = [frameset_data[1],
                             frameset_data[2],
                             frameset_data[0],
                             frameset_data[3]]
        elif (self.channels == 5):
            frameset_data = [frameset_data[1],
                             frameset_data[2],
                             frameset_data[0],
                             frameset_data[3],
                             frameset_data[4]]
        elif (self.channels == 6):
            frameset_data = [frameset_data[1],
                             frameset_data[2],
                             frameset_data[0],
                             frameset_data[5],
                             frameset_data[3],
                             frameset_data[4]]
        elif (self.channels == 7):
            frameset_data = [frameset_data[1],
                             frameset_data[2],
                             frameset_data[0],
                             frameset_data[6],
                             frameset_data[3],
                             frameset_data[4],
                             frameset_data[5]]
        elif (self.channels == 8):
            frameset_data = [frameset_data[3],
                             frameset_data[4],
                             frameset_data[0],
                             frameset_data[7],
                             frameset_data[5],
                             frameset_data[6],
                             frameset_data[1],
                             frameset_data[2]]
        else:
            raise ValueError("unsupported channel count")

        framelist = from_channels([from_list(channel,
                                             1,
                                             self.bits_per_sample,
                                             True)
                                   for channel in frameset_data])

        #deduct PCM frames from remainder
        self.total_pcm_frames -= framelist.frames

        #return samples as a pcm.FrameList object
        return framelist

    def read_frame(self, channel_count):
        """returns a list of PCM sample lists, one per channel"""

        #read the ALAC frame header
        self.reader.skip(16)
        has_sample_count = self.reader.read(1)
        uncompressed_lsb_size = self.reader.read(2)
        uncompressed = self.reader.read(1)
        if (has_sample_count):
            sample_count = self.reader.read(32)
        else:
            sample_count = self.samples_per_frame

        if (uncompressed == 1):
            #if the frame is uncompressed,
            #read the raw, interlaced samples
            samples = [self.reader.read_signed(self.bits_per_sample)
                       for i in xrange(sample_count * channel_count)]
            return [samples[i::channel_count] for i in xrange(channel_count)]
        else:
            #if the frame is compressed,
            #read the interlacing parameters
            interlacing_shift = self.reader.read(8)
            interlacing_leftweight = self.reader.read(8)

            #subframe headers
            subframe_headers = [self.read_subframe_header()
                                for i in xrange(channel_count)]

            #optional uncompressed LSB values
            if (uncompressed_lsb_size > 0):
                uncompressed_lsbs = [
                    self.reader.read(uncompressed_lsb_size * 8)
                    for i in xrange(sample_count * channel_count)]
            else:
                uncompressed_lsbs = []

            sample_size = (self.bits_per_sample -
                           (uncompressed_lsb_size * 8) +
                           channel_count - 1)

            #and residual blocks
            residual_blocks = [self.read_residuals(sample_size,
                                                   sample_count)
                               for i in xrange(channel_count)]

            #calculate subframe samples based on
            #subframe header's QLP coefficients and QLP shift-needed
            decoded_subframes = [self.decode_subframe(header[0],
                                                      header[1],
                                                      sample_size,
                                                      residuals)
                                 for (header, residuals) in
                                 zip(subframe_headers,
                                     residual_blocks)]

            #decorrelate channels according interlacing shift and leftweight
            decorrelated_channels = self.decorrelate_channels(
                decoded_subframes,
                interlacing_shift,
                interlacing_leftweight)

            #if uncompressed LSB values are present,
            #prepend them to each sample of each channel
            if (uncompressed_lsb_size > 0):
                channels = []
                for (i, channel) in enumerate(decorrelated_channels):
                    assert(len(channel) ==
                           len(uncompressed_lsbs[i::channel_count]))
                    channels.append([s << (uncompressed_lsb_size * 8) | l
                                     for (s, l) in
                                     zip(channel,
                                         uncompressed_lsbs[i::channel_count])])
                return channels
            else:
                return decorrelated_channels

    def read_subframe_header(self):
        prediction_type = self.reader.read(4)
        qlp_shift_needed = self.reader.read(4)
        rice_modifier = self.reader.read(3)
        qlp_coefficients = [self.reader.read_signed(16)
                            for i in xrange(self.reader.read(5))]

        return (qlp_shift_needed, qlp_coefficients)

    def read_residuals(self, sample_size, sample_count):
        residuals = []
        history = self.initial_history
        sign_modifier = 0
        i = 0

        while (i < sample_count):
            #get an unsigned residual based on "history"
            #and on "sample_size" as a lst resort
            k = min(log2(history // (2 ** 9) + 3), self.maximum_k)

            unsigned = self.read_residual(k, sample_size) + sign_modifier

            #clear out old sign modifier, if any
            sign_modifier = 0

            #change unsigned residual to signed residual
            if (unsigned & 1):
                residuals.append(-((unsigned + 1) // 2))
            else:
                residuals.append(unsigned // 2)

            #update history based on unsigned residual
            if (unsigned <= 0xFFFF):
                history += ((unsigned * self.history_multiplier) -
                            ((history * self.history_multiplier) >> 9))
            else:
                history = 0xFFFF

            #if history gets too small, we may have a block of 0 samples
            #which can be compressed more efficiently
            if ((history < 128) and ((i + 1) < sample_count)):
                zeroes_k = min(7 -
                               log2(history) +
                               ((history + 16) // 64),
                               self.maximum_k)
                zero_residuals = self.read_residual(zeroes_k, 16)
                if (zero_residuals > 0):
                    residuals.extend([0] * zero_residuals)
                    i += zero_residuals

                history = 0

                if (zero_residuals <= 0xFFFF):
                    sign_modifier = 1

            i += 1

        return residuals

    def read_residual(self, k, sample_size):
        msb = self.reader.limited_unary(0, 9)
        if (msb is None):
            return self.reader.read(sample_size)
        elif (k == 0):
            return msb
        else:
            lsb = self.reader.read(k)
            if (lsb > 1):
                return msb * ((1 << k) - 1) + (lsb - 1)
            elif (lsb == 1):
                self.reader.unread(1)
                return msb * ((1 << k) - 1)
            else:
                self.reader.unread(0)
                return msb * ((1 << k) - 1)

    def decode_subframe(self, qlp_shift_needed, qlp_coefficients,
                        sample_size, residuals):
        #first sample is always copied verbatim
        samples = [residuals.pop(0)]

        if (len(qlp_coefficients) < 31):
            #the next "coefficient count" samples
            #are applied as differences to the previous
            for i in xrange(len(qlp_coefficients)):
                samples.append(truncate_bits(samples[-1] + residuals.pop(0),
                                             sample_size))

            #remaining samples are processed much like LPC
            for residual in residuals:
                base_sample = samples[-len(qlp_coefficients) - 1]
                lpc_sum = sum([(s - base_sample) * c for (s, c) in
                               zip(samples[-len(qlp_coefficients):],
                                   reversed(qlp_coefficients))])
                outval = (1 << (qlp_shift_needed - 1)) + lpc_sum
                outval >>= qlp_shift_needed
                samples.append(truncate_bits(outval + residual + base_sample,
                                             sample_size))

                buf = samples[-len(qlp_coefficients) - 2:-1]

                #error value then adjusts the coefficients table
                if (residual > 0):
                    predictor_num = len(qlp_coefficients) - 1

                    while ((predictor_num >= 0) and residual > 0):
                        val = (buf[0] -
                               buf[len(qlp_coefficients) - predictor_num])

                        sign = sign_only(val)

                        qlp_coefficients[predictor_num] -= sign

                        val *= sign

                        residual -= ((val >> qlp_shift_needed) *
                                     (len(qlp_coefficients) - predictor_num))

                        predictor_num -= 1

                elif (residual < 0):
                    #the same as above, but we break if residual goes positive
                    predictor_num = len(qlp_coefficients) - 1

                    while ((predictor_num >= 0) and residual < 0):
                        val = (buf[0] -
                               buf[len(qlp_coefficients) - predictor_num])

                        sign = -sign_only(val)

                        qlp_coefficients[predictor_num] -= sign

                        val *= sign

                        residual -= ((val >> qlp_shift_needed) *
                                     (len(qlp_coefficients) - predictor_num))

                        predictor_num -= 1
        else:
            #residuals are encoded as simple difference values
            for residual in residuals:
                samples.append(truncate_bits(samples[-1] + residual,
                                             sample_size))

        return samples

    def decorrelate_channels(self, channel_data,
                             interlacing_shift, interlacing_leftweight):
        if (len(channel_data) != 2):
            return channel_data
        elif (interlacing_leftweight == 0):
            return channel_data
        else:
            left = []
            right = []
            for (ch1, ch2) in zip(*channel_data):
                right.append(ch1 - ((ch2 * interlacing_leftweight) //
                                    (2 ** interlacing_shift)))
                left.append(ch2 + right[-1])
            return [left, right]

    def close(self):
        pass
