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
from audiotools import BufferedPCMReader
from hashlib import md5


def encode_wavpack(filename, pcmreader):
    pass

def correlation_pass_1ch(uncorrelated_samples,
                         term, delta, weight, correlation_samples):
    if (term == 18):
        assert(len(correlation_samples) == 2)
        uncorrelated = ([correlation_samples[1],
                         correlation_samples[0]] +
                        uncorrelated_samples)
        correlated = []
        for i in xrange(2, len(uncorrelated)):
            temp = (3 * uncorrelated[i - 1] - uncorrelated[i - 2]) / 2
            correlated.append(uncorrelated[i] - apply_weight(weight, temp))
            weight += update_weight(temp, correlated[i - 2], delta)
        return correlated
    elif (term == 17):
        assert(len(correlation_samples) == 2)
        uncorrelated = ([correlation_samples[1],
                         correlation_samples[0]] +
                        uncorrelated_samples)
        correlated = []
        for i in xrange(2, len(uncorrelated)):
            temp = 2 * uncorrelated[i - 1] - uncorrelated[i - 2]
            correlated.append(uncorrelated[i] - apply_weight(weight, temp))
            weight += update_weight(temp, correlated[i - 2], delta)
        return correlated
    elif ((1 <= term) and (term <= 8)):
        assert(len(correlation_samples) == term)
        uncorrelated = correlation_samples[:] + uncorrelated_samples
        correlated = []
        for i in xrange(term, len(uncorrelated)):
            correlated.append(uncorrelated[i] -
                              apply_weight(weight, uncorrelated[i - term]))
            weight += update_weight(uncorrelated[i - term],
                                    correlated[i - term], delta)
        return correlated
    else:
        raise ValueError("unsupported term")

def correlation_pass_2ch(uncorrelated_samples,
                         term, delta, weights, correlation_samples):
    assert(len(uncorrelated_samples) == 2)
    assert(len(uncorrelated_samples[0]) == len(uncorrelated_samples[1]))
    assert(len(weights) == 2)

    if (((17 <= term) and (term <= 18)) or ((1 <= term) and (term <= 8))):
        return (correlation_pass_1ch(uncorrelated_samples[0],
                                     term, delta, weights[0],
                                     correlation_samples[0]),
                correlation_pass_1ch(uncorrelated_samples[1],
                                     term, delta, weights[1],
                                     correlation_samples[1]))
    elif ((-3 <= term) and (term <= -1)):
        assert(len(correlation_samples[0]) == 1)
        assert(len(correlation_samples[1]) == 1)
        uncorrelated = (correlation_samples[1] + uncorrelated_samples[0],
                        correlation_samples[0] + uncorrelated_samples[1])
        correlated = [[], []]
        weights = list(weights)
        if (term == -1):
            for i in xrange(1, len(uncorrelated[0])):
                correlated[0].append(uncorrelated[0][i] -
                                     apply_weight(weights[0],
                                                  uncorrelated[1][i - 1]))
                correlated[1].append(uncorrelated[1][i] -
                                     apply_weight(weights[1],
                                                  uncorrelated[0][i]))
                weights[0] += update_weight(uncorrelated[1][i - 1],
                                            correlated[0][-1],
                                            delta)
                weights[1] += update_weight(uncorrelated[0][i],
                                            correlated[1][-1],
                                            delta)
                weights[0] = max(min(weights[0], 1024), -1024)
                weights[1] = max(min(weights[1], 1024), -1024)
        elif (term == -2):
            for i in xrange(1, len(uncorrelated[0])):
                correlated[0].append(uncorrelated[0][i] -
                                     apply_weight(weights[0],
                                                  uncorrelated[1][i]))
                correlated[1].append(uncorrelated[1][i] -
                                     apply_weight(weights[1],
                                                  uncorrelated[0][i - 1]))
                weights[0] += update_weight(uncorrelated[1][i],
                                            correlated[0][-1],
                                            delta)
                weights[1] += update_weight(uncorrelated[0][i - 1],
                                            correlated[1][-1],
                                            delta)
                weights[0] = max(min(weights[0], 1024), -1024)
                weights[1] = max(min(weights[1], 1024), -1024)
        elif (term == -3):
            for i in xrange(1, len(uncorrelated[0])):
                correlated[0].append(uncorrelated[0][i] -
                                     apply_weight(weights[0],
                                                  uncorrelated[1][i - 1]))
                correlated[1].append(uncorrelated[1][i] -
                                     apply_weight(weights[1],
                                                  uncorrelated[0][i - 1]))
                weights[0] += update_weight(uncorrelated[1][i - 1],
                                            correlated[0][-1],
                                            delta)
                weights[1] += update_weight(uncorrelated[0][i - 1],
                                            correlated[1][-1],
                                            delta)
                weights[0] = max(min(weights[0], 1024), -1024)
                weights[1] = max(min(weights[1], 1024), -1024)

        return correlated
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

def store_weight(w):
    raise NotImplementedError()

def restore_weight(v):
    raise NotImplementedError()

LOG2 = [0x00, 0x01, 0x03, 0x04, 0x06, 0x07, 0x09, 0x0a,
        0x0b, 0x0d, 0x0e, 0x10, 0x11, 0x12, 0x14, 0x15,
        0x16, 0x18, 0x19, 0x1a, 0x1c, 0x1d, 0x1e, 0x20,
        0x21, 0x22, 0x24, 0x25, 0x26, 0x28, 0x29, 0x2a,
        0x2c, 0x2d, 0x2e, 0x2f, 0x31, 0x32, 0x33, 0x34,
        0x36, 0x37, 0x38, 0x39, 0x3b, 0x3c, 0x3d, 0x3e,
        0x3f, 0x41, 0x42, 0x43, 0x44, 0x45, 0x47, 0x48,
        0x49, 0x4a, 0x4b, 0x4d, 0x4e, 0x4f, 0x50, 0x51,
        0x52, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a,
        0x5c, 0x5d, 0x5e, 0x5f, 0x60, 0x61, 0x62, 0x63,
        0x64, 0x66, 0x67, 0x68, 0x69, 0x6a, 0x6b, 0x6c,
        0x6d, 0x6e, 0x6f, 0x70, 0x71, 0x72, 0x74, 0x75,
        0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d,
        0x7e, 0x7f, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85,
        0x86, 0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d,
        0x8e, 0x8f, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95,
        0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b, 0x9b, 0x9c,
        0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4,
        0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xa9, 0xaa, 0xab,
        0xac, 0xad, 0xae, 0xaf, 0xb0, 0xb1, 0xb2, 0xb2,
        0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xb9,
        0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf, 0xc0, 0xc0,
        0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc6, 0xc7,
        0xc8, 0xc9, 0xca, 0xcb, 0xcb, 0xcc, 0xcd, 0xce,
        0xcf, 0xd0, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd4,
        0xd5, 0xd6, 0xd7, 0xd8, 0xd8, 0xd9, 0xda, 0xdb,
        0xdc, 0xdc, 0xdd, 0xde, 0xdf, 0xe0, 0xe0, 0xe1,
        0xe2, 0xe3, 0xe4, 0xe4, 0xe5, 0xe6, 0xe7, 0xe7,
        0xe8, 0xe9, 0xea, 0xea, 0xeb, 0xec, 0xed, 0xee,
        0xee, 0xef, 0xf0, 0xf1, 0xf1, 0xf2, 0xf3, 0xf4,
        0xf4, 0xf5, 0xf6, 0xf7, 0xf7, 0xf8, 0xf9, 0xf9,
        0xfa, 0xfb, 0xfc, 0xfc, 0xfd, 0xfe, 0xff, 0xff]

def wv_log2(value):
    from math import log

    a = abs(value) + (abs(value) / 2 ** 9)
    if (a != 0):
        c = int(log(a)  / log(2)) + 1
    else:
        c = 0
    if (value >= 0):
        if ((0 <= a) and (a < 256)):
            return c * 2 ** 8 + LOG2[(a * 2 ** (9 - c)) % 256]
        else:
            return c * 2 ** 8 + LOG2[(a / 2 ** (c - 9)) % 256]
    else:
        if ((0 <= a) and (a < 256)):
            return -(c * 2 ** 8 + LOG2[(a * 2 ** (9 - c)) % 256])
        else:
            return -(c * 2 ** 8 + LOG2[(a / 2 ** (c - 9)) % 256])


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

def wv_exp2(value):
    if ((-32768 <= value) and (value < -2304)):
        return -(EXP2[-value & 0xFF] << ((-value >> 8) - 9))
    elif ((-2304 <= value) and (value < 0)):
        return -(EXP2[-value & 0xFF] >> (9 - (-value >> 8)))
    elif ((0 <= value) and (value <= 2304)):
        return EXP2[value & 0xFF] >> (9 - (value >> 8))
    elif ((2304 < value) and (value <= 32767)):
        return EXP2[value & 0xFF] << ((value >> 8) - 9)
    else:
        raise ValueError("%s not a signed 16-bit value" % (value))

def write_bitstream(writer, channels, entropies):
    from math import log

    assert((len(channels) == 1) or (len(channels) == 2))
    assert(len(set(map(len, channels))) == 1)

    u = None
    i = 0
    total_samples = len(channels) * len(channels[0])
    signs = []
    ms = []
    bases = []
    adds = []
    while (i < total_samples):
        sample = channels[i % len(channels)][i / len(channels)]
        if ((u is None) and (entropies[0][0] < 2) and (entropies[1][0] < 2)):
            #handle long run of 0 residuals
            raise NotImplementedError()
        else:
            if (sample >= 0):
                unsigned = sample
                signs.append(0)
            else:
                unsigned = -sample - 1
                signs.append(1)

            entropy = entropies[i % len(channels)]
            medians = [e / 2 ** 4 + 1 for e in entropy]

            if (unsigned < medians[0]):
                m = 0
                base = 0
                add = entropy[0] >> 4
                entropy[0] -= ((entropy[0] + 126) / 128) * 2
            elif ((unsigned - medians[0]) < medians[1]):
                m = 1
                base = medians[0]
                add = entropy[1] >> 4
                entropy[0] += ((entropy[0] + 128) / 128) * 5
                entropy[1] -= ((entropy[1] + 62) / 64) * 2
            elif ((unsigned - (medians[0] + medians[1])) < medians[2]):
                m = 2
                base = medians[0] + medians[1]
                add = entropy[2] >> 4
                entropy[0] += ((entropy[0] + 128) / 128) * 5
                entropy[1] += ((entropy[1] + 64) / 64) * 5
                entropy[2] -= ((entropy[2] + 30) / 32) * 2
            else:
                m = ((unsigned - (medians[0] + medians[1])) / medians[2]) + 2
                base = medians[0] + medians[1] + ((m - 2) * medians[2])
                add = entropy[2] >> 4
                entropy[0] += ((entropy[0] + 128) / 128) * 5
                entropy[1] += ((entropy[1] + 64) / 64) * 5
                entropy[2] += ((entropy[2] + 32) / 32) * 5

            bases.append(base)
            adds.append(add)

            if (add == 0):
                print "fixed size = 0"
            else:
                e = 2 ** (int(log(add) / log(2)) + 1) - add - 1
                p = int(log(add) / log(2))
                if ((unsigned - base) < e):
                    r = unsigned - base
                    b = None
                else:
                    r = (unsigned - base + e) / 2
                    b = (unsigned - base + e) % 2
                print "p %s  r %s  e %s  b %s" % (p, r, e, b)


            i += 1
    print bases
    print entropies
    print signs

def write_residual(writer, unsigned, prev_u, m, next_m, base, add, sign):
    """given u_(i - 1), m_(i) and m_(i + 1)
    along with base_(i) and add_(i) values,
    writes the given residual to the output stream
    and returns u_(i)
    """

    from math import log

    #determine u_(i)
    if ((m > 0) and (next_m > 0)):
        #positive m to positive m
        if ((prev_u is not None) and (prev_u % 2 == 1)):
            #passing 1 from previous u
            u_i = (m * 2) - 1
        else:
            u_i = (m * 2) + 1
    elif ((m == 0) and (next_m > 0)):
        if ((prev_u is not None) and (prev_u % 2 == 0)):
            #passing 0 from previous u
            u_i = None
        else:
            u_i = 1
    elif ((m > 0) and (next_m == 0)):
        if ((prev_u is not None) and (prev_u % 2 == 1)):
            #passing 1 from previous u
            u_i = (m - 1) * 2
        else:
            u_i = m * 2
    elif ((m == 0) and (next_m == 0)):
        if ((prev_u is not None) and (prev_u % 2 == 0)):
            #passing 0 from previous u
            u_i = None
        else:
            u_i = 0
    else:
        raise ValueError("invalid m")

    if (u_i is not None):
        if (u_i < 16):
            writer.unary(0, u_i)
        else:
            writer.unary(0, 16)
            write_egc(writer, u_i - 16)

    if (add > 0):
        e = 2 ** (int(log(add) / log(2)) + 1) - add - 1
        p = int(log(add) / log(2))
        if ((unsigned - base) < e):
            r = unsigned - base
            b = None
        else:
            r = (unsigned - base + e) / 2
            b = (unsigned - base + e) % 2
        writer.write(p, r)
        if (b is not None):
            writer.write(1, b)

    writer.write(1, sign)

    return u_i

def write_egc(writer, value):
    raise NotImplementedError()

if (__name__ == '__main__'):
    from audiotools.bitstream import BitstreamWriter
    import sys

    w = BitstreamWriter(open(sys.argv[1], "wb"), 1)

    prev_u = None
    for (unsigned, m, next_m, base, add, sign) in zip(
        [60, 31, 32, 32, 17, 36, 1, 37, 20, 35, 35, 31, 50, 25, 62, 18, 68, 10, 71, 0],
        [3, 2, 2, 2, 1, 3, 0, 2, 1, 2, 2, 2, 3, 1, 3, 1, 3, 0, 3, 0],
        [2, 2, 2, 1, 3, 0, 2, 1, 2, 2, 2, 3, 1, 3, 1, 3, 0, 3, 0, 0],
        [42, 20, 22, 20, 9, 34, 0, 24, 9, 26, 24, 27, 46, 11, 53, 12, 58, 0, 65, 0],
        [20, 13, 23, 12, 14, 11, 8, 13, 14, 12, 22, 11, 20, 18, 24, 17, 28, 11, 32, 11],
        [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]):
        prev_u = write_residual(w, unsigned, prev_u, m, next_m, base, add, sign)

    w.byte_align()
    # medians = [[118, 194, 322], [118, 176, 212]]
    # channels = [[-61, -33, -18, 1, 20, 35, 50, 62, 68, 71],
    #             [31, 32, 36, 37, 35, 31, 25, 18, 10, 0]]

    # write_bitstream(None, channels, medians)
