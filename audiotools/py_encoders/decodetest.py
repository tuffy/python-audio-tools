#!/usr/bin/python

from math import log

def read_bitstream(channel_count, block_samples, medians, sub_block_data):
    if (channel_count == 2):
        residuals = ([], [])
    else:
        residuals = ([], )

    u = None
    i = 0
    while (i < (block_samples * channel_count)):
        if ((u is None) and (medians[0][0] < 2) and (medians[1][0] < 2)):
            #handle long run of 0 residuals
            zeroes = read_egc(sub_block_data)
            if (zeroes > 0):
                for j in xrange(zeroes):
                    residuals[i % channel_count].append(0)
                    i += 1
                medians = ([0, 0, 0], [0, 0, 0])
            if (i < (block_samples * channel_count)):
                (residual, u) = read_residual(
                    sub_block_data,
                    u,
                    medians[i % channel_count])
                print "residual[%d] = %d" % (i, residual)
                residuals[i % channel_count].append(residual)
                i += 1
        else:
            (residual, u) = read_residual(
                sub_block_data,
                u,
                medians[i % channel_count])
            print "residual[%d] = %d" % (i, residual)
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


def read_residual(reader, last_u, medians):
    if (last_u is None):
        u = reader.unary(0)
        if (u == 16):
            u += read_egc(reader)
        m = u / 2
    elif ((last_u % 2) == 1):
        u = reader.unary(0)
        if (u == 16):
            u += read_egc(reader)
        m = (u / 2) + 1
    else:
        u = None
        m = 0

    if (m == 0):
        base = 0
        add = medians[0] >> 4
        medians[0] -= ((medians[0] + 126) >> 7) * 2
    elif (m == 1):
        base = (medians[0] >> 4) + 1
        add = medians[1] >> 4
        medians[0] += ((medians[0] + 128) >> 7) * 5
        medians[1] -= ((medians[1] + 62) >> 6) * 2
    elif (m == 2):
        base = ((medians[0] >> 4) + 1) + ((medians[1] >> 4) + 1)
        add = medians[2] >> 4
        medians[0] += ((medians[0] + 128) >> 7) * 5
        medians[1] += ((medians[1] + 64) >> 6) * 5
        medians[2] -= ((medians[2] + 30) >> 5) * 2
    else:
        base = (((medians[0] >> 4) + 1) +
                ((medians[1] >> 4) + 1) +
                (((medians[2] >> 4) + 1) * (m - 2)))
        add = medians[2] >> 4
        medians[0] += ((medians[0] + 128) >> 7) * 5
        medians[1] += ((medians[1] + 64) >> 6) * 5
        medians[2] += ((medians[2] + 32) >> 5) * 5

    if (add == 0):
        unsigned = base
    else:
        p = int(log(add) / log(2))
        r = reader.read(p)
        e = 2 ** (p + 1) - add - 1
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

if (__name__ == '__main__'):
    import sys
    from audiotools.bitstream import BitstreamReader

    print read_bitstream(2, 10, [[118, 194, 322], [118, 176, 212]],
                         BitstreamReader(open(sys.argv[1], "rb"), 1))
