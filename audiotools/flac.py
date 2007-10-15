#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007  Brian Langenberger

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

import array
import audiotools
import sys,cStringIO

Con = audiotools.Con

class UTF8(Con.Struct):
    @classmethod
    def __total_utf8_bytes__(cls, header):
        total = 0
        for b in header:
            if b == '\x01':
                total += 1
            else:
                break
        return max(1,total)

    @classmethod
    def __calculate_utf8_value__(cls, ctx):
        import operator
    
        return Con.lib.bin_to_int(ctx.header[ctx.header.index('\x00') + 1:] + \
                                  reduce(operator.concat,
                                         [s[2:] for s in ctx['sub_byte']],
                                         ''))
    
    def __init__(self, name):
        Con.Struct.__init__(
            self,name,
            Con.Bytes('header',8),
            Con.Value('total_bytes',
                      lambda ctx: self.__total_utf8_bytes__(ctx['header'])),
            Con.MetaRepeater(
            lambda ctx: self.__total_utf8_bytes__(ctx['header']) - 1,
            Con.Bytes('sub_byte',8)),
            Con.Value('value',
                      lambda ctx: self.__calculate_utf8_value__(ctx)))

class Unary(Con.Adapter):
    def __init__(self, name):
        Con.Adapter.__init__(
            self,
            Con.RepeatUntil(lambda obj,ctx: obj == 1,
                            Con.Byte(name)))

    def _encode(self, value, context):
        if (value > 0):
            return ([0] * (value)) + [1]
        else:
            return [1]

    def _decode(self, obj, context):
        return len(obj) - 1

class PlusOne(Con.Adapter):
    def _encode(self, value, context):
        return value - 1

    def _decode(self, obj, context):
        return obj + 1

class FlacStreamException(Exception): pass

class FlacReader:
    FRAME_HEADER = Con.Struct('frame_header',
                              Con.Bits('sync',14),
                              Con.Bits('reserved',2),
                              Con.Bits('block_size',4),
                              Con.Bits('sample_rate',4),
                              Con.Bits('channel_assignment',4),
                              Con.Bits('bits_per_sample',3),
                              Con.Padding(1),
                              Con.IfThenElse(
        'total_channels',
        lambda ctx1: ctx1['channel_assignment'] <= 7,
        Con.Value('c',lambda ctx2: ctx2['channel_assignment'] + 1),
        Con.Value('c',lambda ctx3: 2)),
                              
                              UTF8('frame_number'),
                              
                              Con.IfThenElse(
        'extended_block_size',
        lambda ctx1: ctx1['block_size'] == 6,
        Con.Bits('b',8),
        Con.If(lambda ctx2: ctx2['block_size'] == 7,
               Con.Bits('b',16))),
                              
                              Con.IfThenElse(
        'extended_sample_rate',
        lambda ctx1: ctx1['sample_rate'] == 12,
        Con.Bits('s',8),
        Con.If(lambda ctx2: ctx2['sample_rate'] in (13,14),
               Con.Bits('s',16))),

                              Con.Bits('crc8',8))

    UNARY = Con.Struct('unary',
                       Con.RepeatUntil(
        lambda obj,ctx: obj == '\x01',
        Con.Field('bytes',1)),
                       Con.Value('value',
                                 lambda ctx: len(ctx['bytes']) - 1)
                       )

    SUBFRAME_HEADER = Con.Struct('subframe_header',
                                 Con.Padding(1),
                                 Con.Bits('subframe_type',6),
                                 Con.Flag('has_wasted_bits_per_sample'),
                                 Con.IfThenElse(
        'wasted_bits_per_sample',
        lambda ctx: ctx['has_wasted_bits_per_sample'],
        PlusOne(Unary('value')),
        Con.Value('value',lambda ctx2: 0)))


    GET_BLOCKSIZE_FROM_STREAMINFO = -1
    GET_8BIT_BLOCKSIZE_FROM_END_OF_HEADER = -2
    GET_16BIT_BLOCKSIZE_FROM_END_OF_HEADER = -3

    BLOCK_SIZE = (GET_BLOCKSIZE_FROM_STREAMINFO,
                  192,
                  576,1152,2304,4608,
                  GET_8BIT_BLOCKSIZE_FROM_END_OF_HEADER,
                  GET_16BIT_BLOCKSIZE_FROM_END_OF_HEADER,
                  256,512,1024,2048,4096,8192,16384,32768)

    GET_SAMPLE_SIZE_FROM_STREAMINFO = -1
    SAMPLE_SIZE = (GET_SAMPLE_SIZE_FROM_STREAMINFO,
                   8,12,None,16,20,24,None)

    def FIXED0(subframe,residual,i):
        subframe.insert(i,
                        residual[i])

    def FIXED1(subframe,residual,i):
        subframe.insert(i,
                        subframe[i - 1] + residual[i])

    def FIXED2(subframe,residual,i):
        subframe.insert(i,
                        ((2 * subframe[i - 1]) - subframe[i - 2] + \
                         residual[i]))

    def FIXED3(subframe,residual,i):
        subframe.insert(i,
                        ((3 * subframe[i - 1]) - (3 * subframe[i - 2]) + \
                         subframe[i - 3] + residual[i]))

    def FIXED4(subframe,residual,i):
        subframe.insert(i,
                        ((4 * subframe[i - 1]) - (6 * subframe[i - 2]) + \
                         (4 * subframe[i - 3]) - subframe[i - 4] + residual[i]))

    #iterates over all of the channels, in order
    def MERGE_INDEPENDENT(channel_list):
        channel_data = [iter(c) for c in channel_list]

        while (True):
            for channel in channel_data:
                yield channel.next()

    def MERGE_LEFT(channel_list):
        channel_left = iter(channel_list[0])
        channel_side = iter(channel_list[1])

        while (True):
            left = channel_left.next()
            side = channel_side.next()

            yield left
            yield left - side


    def MERGE_RIGHT(channel_list):
        channel_side = iter(channel_list[0])
        channel_right = iter(channel_list[1])

        while (True):
            side = channel_side.next()
            right = channel_right.next()

            yield side + right
            yield right

    def MERGE_MID(channel_list):
        channel_mid = iter(channel_list[0])
        channel_side = iter(channel_list[1])

        while (True):
            mid = channel_mid.next()
            side = channel_side.next()

            mid = mid << 1
            mid |= (side & 0x1)

            yield (mid + side) >> 1
            yield (mid - side) >> 1


    CHANNEL_FUNCTIONS = (MERGE_INDEPENDENT,
                         MERGE_INDEPENDENT,
                         MERGE_INDEPENDENT,
                         MERGE_INDEPENDENT,
                         MERGE_INDEPENDENT,
                         MERGE_INDEPENDENT,
                         MERGE_INDEPENDENT,
                         MERGE_INDEPENDENT,
                         MERGE_LEFT,
                         MERGE_RIGHT,
                         MERGE_MID)

    FIXED_FUNCTIONS = (FIXED0,FIXED1,FIXED2,FIXED3,FIXED4)

    def __init__(self, flac_stream):
        self.stream = BufferedStream(flac_stream)
        self.streaminfo = None
        self.bitstream = None

        #ensure the file starts with 'fLaC'
        self.read_stream_marker()

        #initialize self.bitstream
        self.begin_bitstream()

        #find self.streaminfo in case we need it
        self.read_metadata_blocks()

    def close(self):
        if (self.bitstream != None):
            self.bitstream.close()
        else:
            self.stream.close()
        

    def read_stream_marker(self):
        if (self.stream.read(4) != 'fLaC'):
            raise FlacStreamException('invalid stream marker')

    def read_metadata_blocks(self):
        block = audiotools.FlacAudio.METADATA_BLOCK_HEADER.parse_stream(self.stream)
        while (block.last_block == 0):
            if (block.block_type == 0):
                self.streaminfo = audiotools.FlacAudio.STREAMINFO.parse_stream(self.stream)
            else:
                self.stream.seek(block.block_length,1)
                
            block = audiotools.FlacAudio.METADATA_BLOCK_HEADER.parse_stream(self.stream)
        self.stream.seek(block.block_length,1)

    def begin_bitstream(self):
        import bitstream
        
        #self.bitstream = Con.BitStreamReader(self.stream)
        self.bitstream = bitstream.BitStreamReader(self.stream)

    def read_frame(self):
        self.stream.reset_buffer()
        
        try:
            header = FlacReader.FRAME_HEADER.parse_stream(self.bitstream)
        except Con.core.FieldError:
            return ""

        if (header.sync != 0x3FFE):
            raise FlacStreamException('invalid sync')

        if (crc8(self.stream.getvalue()[0:-1]) != header.crc8):
            raise FlacStreamException('crc8 checksum failed')


        #block_size tells us how many samples we need from each subframe
        block_size = FlacReader.BLOCK_SIZE[header.block_size]
        if (block_size == self.GET_BLOCKSIZE_FROM_STREAMINFO):
            block_size = self.streaminfo.maximum_blocksize
            
        elif ((block_size == self.GET_8BIT_BLOCKSIZE_FROM_END_OF_HEADER) or
              (block_size == self.GET_16BIT_BLOCKSIZE_FROM_END_OF_HEADER)):
            block_size = header.extended_block_size + 1


        #grab subframe data as 32-bit array objects
        subframe_data = []

        for channel_number in xrange(header.total_channels):
            subframe_data.append(
                self.read_subframe(header, block_size, channel_number))

        crc16sum = crc16(self.stream.getvalue())
        
            
        #try to byte-align the stream
        if (len(self.bitstream.buffer) > 0):
            self.bitstream.read(len(self.bitstream.buffer))


        if (crc16sum != Con.Bits('crc16',16).parse_stream(self.bitstream)):
            raise FlacStreamException('crc16 checksum failed')
        
        
        #convert our list of subframe data arrays into
        #a string of sample data
        if (FlacReader.SAMPLE_SIZE[header.bits_per_sample] == 16):
            merged_frames = array.array('h',
                                        FlacReader.CHANNEL_FUNCTIONS[
                header.channel_assignment](subframe_data))

            if (audiotools.BIG_ENDIAN):
                merged_frames.byteswap()

            return merged_frames.tostring()
        
        elif (FlacReader.SAMPLE_SIZE[header.bits_per_sample] == 8):
            merged_frames = array.array('b',
                                        FlacReader.CHANNEL_FUNCTIONS[
                header.channel_assignment](subframe_data))

            return merged_frames.tostring()
        
        else:
            if (FlacReader.SAMPLE_SIZE[header.bits_per_sample] == \
                self.GET_SAMPLE_SIZE_FROM_STREAMINFO):
                bits_per_sample = self.streaminfo.bits_per_sample + 1
                
            elif (FlacReader.SAMPLE_SIZE[header.bits_per_sample] == None):
                raise FlacStreamException('invalid bits per sample')
            
            else:
                bits_per_sample = FlacReader.SAMPLE_SIZE[header.bits_per_sample]

            stream = Con.GreedyRepeater(
                Con.BitStruct('bits',
                              Con.Bits('value',bits_per_sample,
                                       swapped=True,signed=True)))

            return stream.build(
                [Con.Container(value=v) for v in
                 FlacReader.CHANNEL_FUNCTIONS[header.channel_assignment](
                    subframe_data)])
            


    def read_subframe(self, frame_header, block_size, channel_number):
        subframe_header = \
                        FlacReader.SUBFRAME_HEADER.parse_stream(self.bitstream)

        #figure out the bits-per-sample of this subframe
        if ((frame_header.channel_assignment == 8) and
            (channel_number == 1)):
            #if channel is stored as left+difference
            #and this is the difference, add 1 bit
            bits_per_sample = FlacReader.SAMPLE_SIZE[
                frame_header.bits_per_sample] + 1
            
        elif ((frame_header.channel_assignment == 9) and
              (channel_number == 0)):
            #if channel is stored as difference+right
            #and this is the difference, add 1 bit
            bits_per_sample = FlacReader.SAMPLE_SIZE[
                frame_header.bits_per_sample] + 1
            
        elif ((frame_header.channel_assignment == 10) and
              (channel_number == 1)):
            #if channel is stored as average+difference
            #and this is the difference, add 1 bit
            bits_per_sample = FlacReader.SAMPLE_SIZE[
                frame_header.bits_per_sample] + 1
            
        else:
            #otherwise, use the number from the frame header
            bits_per_sample = FlacReader.SAMPLE_SIZE[
                frame_header.bits_per_sample]


        if (subframe_header.has_wasted_bits_per_sample):
            bits_per_sample -= subframe_header.wasted_bits_per_sample
        
        if (subframe_header.subframe_type == 0):
            subframe = self.read_subframe_constant(block_size, bits_per_sample)
            
        elif (subframe_header.subframe_type == 1):
            subframe = self.read_subframe_verbatim(block_size, bits_per_sample)
            
        elif ((subframe_header.subframe_type & 0x38) == 0x08):
            subframe = self.read_subframe_fixed(
                subframe_header.subframe_type & 0x07,
                block_size,
                bits_per_sample)
            
        elif ((subframe_header.subframe_type & 0x20) == 0x20):
            subframe = self.read_subframe_lpc(
                (subframe_header.subframe_type & 0x1F) + 1,
                block_size,
                bits_per_sample)
            
        else:
            raise FlacStreamException('invalid subframe type')

        if (subframe_header.has_wasted_bits_per_sample):
            return array.array(
                'i',
                [i << subframe_header.wasted_bits_per_sample
                 for i in subframe])
        else:
            return subframe

    def read_subframe_constant(self, block_size, bits_per_sample):
        sample = Con.Bits('b',bits_per_sample).parse_stream(
            self.bitstream)
        
        subframe = array.array('i',[sample] * block_size)

        return subframe
    

    def read_subframe_verbatim(self, block_size, bits_per_sample):
        return array.array('i',
                           Con.StrictRepeater(
            block_size,
            Con.Bits("samples",
                     bits_per_sample,
                     signed=True)).parse_stream(self.bitstream))


    def read_subframe_fixed(self, order, block_size, bits_per_sample):
        samples = Con.StrictRepeater(
            order,
            Con.Bits("warm_up_samples",
                     bits_per_sample,
                     signed=True))
        
        subframe = array.array('i',
                               samples.parse_stream(self.bitstream))

        residual = self.read_residual(block_size,order)

        fixed_func = self.FIXED_FUNCTIONS[order]
 
        for i in xrange(len(subframe),block_size):
            fixed_func(subframe,residual,i)
            
        return subframe


    def read_subframe_lpc(self, order, block_size, bits_per_sample):       
        samples = Con.StrictRepeater(
            order,
            Con.Bits("warm_up_samples",
                     bits_per_sample,
                     signed=True))

        subframe = array.array('i',
                               samples.parse_stream(self.bitstream))

        lpc_precision = Con.Bits('lpc_precision',
                                 4).parse_stream(self.bitstream) + 1

        lpc_shift = Con.Bits('lpc_shift',
                             5).parse_stream(self.bitstream)

        coefficients = array.array('i',
                                   Con.StrictRepeater(
            order,
            Con.Bits('coefficients',
                     lpc_precision,
                     signed=True)).parse_stream(self.bitstream))
        
        residual = self.read_residual(block_size, order)

        for i in xrange(len(subframe),block_size):
            subframe.insert(i,
                            (sum(
                [coefficients[j] * subframe[i - j - 1] for j in
                 xrange(0,len(coefficients))]) >> lpc_shift) + \
                            residual[i])

        return subframe


    def read_residual(self, block_size, predictor_order):
        rice = array.array('i')

        #add some dummy rice so that the Rice index matches
        #that of the rest of the subframe
        for i in xrange(predictor_order):
            rice.append(0)
        
        if (self.bitstream.read(2) != '\x00\x00'):
            raise FlacStreamException('invalid residual coding method')
        
        partition_order = Con.Bits('partition_order',4).parse_stream(
            self.bitstream)

        if (partition_order > 0):
            total_samples = ((block_size / 2 ** partition_order) -
                             predictor_order)
            rice.extend(self.read_encoded_rice(total_samples))
            
            for i in xrange(1,2 ** partition_order):
                total_samples = (block_size / 2 ** partition_order)
                
                rice.extend(self.read_encoded_rice(total_samples))
        else:
            rice.extend(self.read_encoded_rice(block_size - predictor_order))

        return rice


    def read_encoded_rice(self, total_samples):
        bin_to_int = Con.lib.binary.bin_to_int
        
        samples = array.array('i')

        rice_parameter = Con.Bits('rice_parameter',4).parse_stream(
            self.bitstream)

        if (rice_parameter != 0xF):
            #a Rice encoded residual
            for x in xrange(total_samples):

                #count the number of 0 bits before the next 1 bit
                #(unary encoding)
                #to find our most significant bits            
                msb = 0
                s = self.bitstream.read(1)
                while (s != '\x01'):
                    msb += 1
                    s = self.bitstream.read(1)

                #grab the proper number of least significant bits
                lsb = bin_to_int(self.bitstream.read(rice_parameter))

                #combine msb and lsb to get the Rice-encoded value
                value = (msb << rice_parameter) | lsb
                if ((value & 0x1) == 0x1): #negative
                    samples.append(-(value >> 1) - 1)
                else:                      #positive
                    samples.append(value >> 1)
        else:
            #unencoded residual

            bits_per_sample = Con.Bits('escape_code',5).parse_stream(
                self.bitstream)

            sample = Con.Bits("sample",bits_per_sample,signed=True)

            for x in xrange(total_samples):
                samples.append(sample.parse_stream(self.bitstream))

        return samples


###############################
#Checksum calculation functions
###############################

CRC8TABLE = (0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15,
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
             0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3)

def crc8(data, start=0):
    value = start

    for i in map(ord,data):
        value = CRC8TABLE[value ^ i]

    return value

CRC16TABLE = (0x0000,0x8005,0x800f,0x000a,0x801b,0x001e,0x0014,0x8011,
              0x8033,0x0036,0x003c,0x8039,0x0028,0x802d,0x8027,0x0022,
              0x8063,0x0066,0x006c,0x8069,0x0078,0x807d,0x8077,0x0072,
              0x0050,0x8055,0x805f,0x005a,0x804b,0x004e,0x0044,0x8041,
              0x80c3,0x00c6,0x00cc,0x80c9,0x00d8,0x80dd,0x80d7,0x00d2,
              0x00f0,0x80f5,0x80ff,0x00fa,0x80eb,0x00ee,0x00e4,0x80e1,
              0x00a0,0x80a5,0x80af,0x00aa,0x80bb,0x00be,0x00b4,0x80b1,
              0x8093,0x0096,0x009c,0x8099,0x0088,0x808d,0x8087,0x0082,
              0x8183,0x0186,0x018c,0x8189,0x0198,0x819d,0x8197,0x0192,
              0x01b0,0x81b5,0x81bf,0x01ba,0x81ab,0x01ae,0x01a4,0x81a1,
              0x01e0,0x81e5,0x81ef,0x01ea,0x81fb,0x01fe,0x01f4,0x81f1,
              0x81d3,0x01d6,0x01dc,0x81d9,0x01c8,0x81cd,0x81c7,0x01c2,
              0x0140,0x8145,0x814f,0x014a,0x815b,0x015e,0x0154,0x8151,
              0x8173,0x0176,0x017c,0x8179,0x0168,0x816d,0x8167,0x0162,
              0x8123,0x0126,0x012c,0x8129,0x0138,0x813d,0x8137,0x0132,
              0x0110,0x8115,0x811f,0x011a,0x810b,0x010e,0x0104,0x8101,
              0x8303,0x0306,0x030c,0x8309,0x0318,0x831d,0x8317,0x0312,
              0x0330,0x8335,0x833f,0x033a,0x832b,0x032e,0x0324,0x8321,
              0x0360,0x8365,0x836f,0x036a,0x837b,0x037e,0x0374,0x8371,
              0x8353,0x0356,0x035c,0x8359,0x0348,0x834d,0x8347,0x0342,
              0x03c0,0x83c5,0x83cf,0x03ca,0x83db,0x03de,0x03d4,0x83d1,
              0x83f3,0x03f6,0x03fc,0x83f9,0x03e8,0x83ed,0x83e7,0x03e2,
              0x83a3,0x03a6,0x03ac,0x83a9,0x03b8,0x83bd,0x83b7,0x03b2,
              0x0390,0x8395,0x839f,0x039a,0x838b,0x038e,0x0384,0x8381,
              0x0280,0x8285,0x828f,0x028a,0x829b,0x029e,0x0294,0x8291,
              0x82b3,0x02b6,0x02bc,0x82b9,0x02a8,0x82ad,0x82a7,0x02a2,
              0x82e3,0x02e6,0x02ec,0x82e9,0x02f8,0x82fd,0x82f7,0x02f2,
              0x02d0,0x82d5,0x82df,0x02da,0x82cb,0x02ce,0x02c4,0x82c1,
              0x8243,0x0246,0x024c,0x8249,0x0258,0x825d,0x8257,0x0252,
              0x0270,0x8275,0x827f,0x027a,0x826b,0x026e,0x0264,0x8261,
              0x0220,0x8225,0x822f,0x022a,0x823b,0x023e,0x0234,0x8231,
              0x8213,0x0216,0x021c,0x8219,0x0208,0x820d,0x8207,0x0202)

def crc16(data, start=0):
    value = start

    for i in map(ord,data):
        value = ((value << 8) ^ CRC16TABLE[(value >> 8) ^ i]) & 0xFFFF

    return value

#BufferedStream stores the data that passes through read()
#so that checksums can be calculated from it.
#Be sure to reset the buffer as needed.
class BufferedStream:
    def __init__(self, stream):
        self.stream = stream
        self.buffer = cStringIO.StringIO()

    def read(self, count):
        s = self.stream.read(count)
        self.buffer.write(s)
        return s

    def seek(self, offset, whence=0):
        self.stream.seek(offset,whence)

    def tell(self):
        return self.stream.tell()

    def close(self):
        self.stream.close()

    def reset_buffer(self):
        self.buffer.close()
        self.buffer = cStringIO.StringIO()

    def getvalue(self):
        return self.buffer.getvalue()


class FlacPCMReader(audiotools.PCMReader):
    #flac_file should be a file-like stream of FLAC data
    def __init__(self, flac_file):
        self.flacreader = FlacReader(flac_file)
        self.sample_rate = self.flacreader.streaminfo.samplerate
        self.channels = self.flacreader.streaminfo.channels + 1
        self.bits_per_sample = self.flacreader.streaminfo.bits_per_sample + 1
        self.process = None

        self.buffer = []

    #this won't return even close to the expected number of bytes
    #(though that won't really break anything)
    def read(self, bytes):
        return self.flacreader.read_frame()

    def close(self):
        self.flacreader.close()
        
