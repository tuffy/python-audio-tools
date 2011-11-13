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
    writer.write(3, len(channels) - 1)

    encode_uncompressed_frame(writer, pcmreader, options, channels)

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
