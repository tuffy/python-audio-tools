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
