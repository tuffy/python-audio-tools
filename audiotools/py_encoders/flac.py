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

    def update(self, framelist):
        self.total_pcm_frames += framelist.frames
        self.md5sum.update(framelist.to_bytes(False, True))

class Encoding_Options:
    def __init__(self, block_size, max_lpc_order,
                 adaptive_mid_side, mid_side,
                 exhaustive_model_search, max_residual_partition_order):
        self.block_size = block_size
        self.max_lpc_order = max_lpc_order
        self.adaptive_mid_side = adaptive_mid_side
        self.mid_side = mid_side
        self.exhaustive_model_search = exhaustive_model_search
        self.max_residual_partition_order = max_residual_partition_order


def encode_flac(filename, pcmreader,
                block_size=4096,
                max_lpc_order=8,
                adaptive_mid_side=False,
                mid_side=True,
                exhaustive_model_search=False,
                max_residual_partition_order=5):

    options = Encoding_Options(block_size,
                               max_lpc_order,
                               adaptive_mid_side,
                               mid_side,
                               exhaustive_model_search,
                               max_residual_partition_order)

    streaminfo = STREAMINFO(block_size, block_size,
                            0, 0,
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
    frame = pcmreader.read(block_size *
                           (pcmreader.bits_per_sample / 8) *
                           pcmreader.channels)

    while (len(frame) > 0):
        streaminfo.update(frame)

        encode_flac_frame(writer, pcmreader, options, frame_number, frame)

        frame_number += 1
        frame = pcmreader.read(block_size *
                               (pcmreader.bits_per_sample / 8) *
                               pcmreader.channels)

    #return to beginning of file and rewrite STREAMINFO block
    output_file.seek(8, 0)
    streaminfo.write(writer)
    writer.close()

def encode_flac_frame(writer, pcmreader, options, frame_number, frame):
    crc16 = CRC16()
    writer.add_callback(crc16.update)

    write_frame_header(writer, pcmreader, frame_number, frame,
                       pcmreader.channels - 1)

    for i in xrange(frame.channels):
        encode_verbatim_subframe(writer,
                                 pcmreader.bits_per_sample,
                                 frame.channel(i))

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
    encoded_block_size = {192:1, 256: 8, 512: 9, 576:2, 1024:10,
                          1152:3, 2048:11, 2304:4, 4096:12,
                          4608:5, 8192:13, 16384:14, 32768:15}.get(frame.frames,
                                                                   None)
    if (encoded_block_size is None):
        if (frame.frames <= 256):
            encoded_block_size = 6
        elif (frame.frames <= 65536):
            encoded_block_size = 7
        else:
            encoded_block_size = 0
    writer.write(4, encoded_block_size)

    encoded_sample_rate = {8000:4, 16000:5, 22050:6, 24000:7, 32000:8,
                           44100:9, 48000:10, 88200:1, 96000:11, 176400:2,
                           192000:3}.get(pcmreader.sample_rate, None)
    if (encoded_sample_rate is None):
        if (((pcmreader.sample_rate % 1000) == 0) and
            (pcmreader.sample_rate <= 255000)):
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

    encoded_bps = {8:1, 12:2, 16:4, 20:5, 24:6}.get(pcmreader.bits_per_sample,
                                                    0)
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
        raise NotImplementedError()


def encode_verbatim_subframe(writer, bits_per_sample, samples):
    writer.build("1u 6u 1u", [0, 1, 0])
    for sample in samples:
        writer.write_signed(bits_per_sample, sample)


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
