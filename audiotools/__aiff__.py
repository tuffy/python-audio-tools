#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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

from audiotools import AudioFile,InvalidFile,Con,PCMReader,__capped_stream_reader__,PCMReaderError,transfer_data,DecodingError,EncodingError,ID3v22Comment,BUFFER_SIZE,ChannelMask,UnsupportedChannelMask,ReorderedPCMReader

import gettext

gettext.install("audiotools",unicode=True)

_HUGE_VAL = 1.79769313486231e+308

class IEEE_Extended(Con.Adapter):
    def __init__(self,name):
        Con.Adapter.__init__(
            self,
            Con.Struct(name,
                       Con.Embed(Con.BitStruct(None,
                                               Con.Flag("signed"),
                                               Con.Bits("exponent",15))),
                       Con.UBInt64("mantissa")))

    def _encode(self, value, context):
        import math

        if (value < 0):
            signed = True
            value *= -1
        else:
            signed = False

        (fmant,exponent) = math.frexp(value)
        if ((exponent > 16384) or (fmant >= 1)):
            exponent = 0x7FFF
            mantissa = 0
        else:
            exponent += 16382
            mantissa = fmant * (2 ** 64)

        return Con.Container(signed=signed,
                             exponent=exponent,
                             mantissa=mantissa)

    def _decode(self, obj, context):
        if ((obj.exponent == 0) and (obj.mantissa == 0)):
            return 0
        else:
            if (obj.exponent == 0x7FFF):
                return _HUGE_VAL
            else:
                f = obj.mantissa * (2.0 ** (obj.exponent - 16383 - 63))
                return f if not obj.signed else -f

#######################
#AIFF
#######################

class AiffException(Exception): pass

class AiffAudio(AudioFile):
    SUFFIX = "aiff"
    NAME = SUFFIX

    AIFF_HEADER = Con.Struct("aiff_header",
                             Con.Const(Con.Bytes("aiff_id",4),"FORM"),
                             Con.UBInt32("aiff_size"),
                             Con.Const(Con.Bytes("aiff_type",4),"AIFF"))

    CHUNK_HEADER = Con.Struct("chunk_header",
                              Con.Bytes("chunk_id",4),
                              Con.UBInt32("chunk_length"))

    COMM_CHUNK = Con.Struct("comm",
                            Con.UBInt16("channels"),
                            Con.UBInt32("total_sample_frames"),
                            Con.UBInt16("sample_size"),
                            IEEE_Extended("sample_rate"))

    SSND_ALIGN = Con.Struct("ssnd",
                            Con.UBInt32("offset"),
                            Con.UBInt32("blocksize"))

    def __init__(self, filename):
        self.filename = filename
        (self.__channels__,
         self.__total_sample_frames__,
         self.__sample_size__,
         self.__sample_rate__) = self.comm_chunk()

    def bits_per_sample(self):
        return self.__sample_size__

    def channels(self):
        return self.__channels__

    def channel_mask(self):
        #this unusual arrangement is taken from the AIFF specification
        if (self.channels() <= 2):
            return ChannelMask.from_channels(self.channels())
        elif (self.channels() == 3):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,front_center=True)
        elif (self.channels() == 4):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,
                back_left=True,back_right=True)
        elif (self.channels() == 6):
            return ChannelMask.from_fields(
                front_left=True,side_left=True,
                front_center=True,front_right=True,
                side_right=True,back_center=True)
        else:
            raise ValueError("undefined channel mask")

    def lossless(self):
        return True

    def total_frames(self):
        return self.__total_sample_frames__

    def sample_rate(self):
        return self.__sample_rate__

    @classmethod
    def is_type(cls, file):
        header = file.read(12)

        return ((header[0:4] == 'FORM') and
                (header[8:12] == 'AIFF'))

    def chunks(self):
        f = open(self.filename,'rb')
        try:
            aiff_header = self.AIFF_HEADER.parse_stream(f)
        except Con.ConstError:
            raise AiffException(_(u"Not an AIFF file"))
        except Con.core.FieldError:
            raise AiffException(_(u"Invalid AIFF file"))

        total_size = aiff_header.aiff_size - 4
        while (total_size > 0):
            chunk_header = self.CHUNK_HEADER.parse_stream(f)
            total_size -= 8
            yield (chunk_header.chunk_id,
                   chunk_header.chunk_length,
                   f.tell())
            f.seek(chunk_header.chunk_length,1)
            total_size -= chunk_header.chunk_length
        f.close()

    def comm_chunk(self):
        for (chunk_id,chunk_length,chunk_offset) in self.chunks():
            if (chunk_id == 'COMM'):
                f = open(self.filename,'rb')
                f.seek(chunk_offset,0)
                comm = self.COMM_CHUNK.parse(f.read(chunk_length))
                f.close()
                return (comm.channels,
                        comm.total_sample_frames,
                        comm.sample_size,
                        int(comm.sample_rate))
        else:
            raise AiffException(_(u"COMM chunk not found"))

    def chunk_files(self):
        f = open(self.filename,'rb')
        try:
            aiff_header = self.AIFF_HEADER.parse_stream(f)
        except Con.ConstError:
            raise AiffException(_(u"Not an AIFF file"))
        except Con.core.FieldError:
            raise AiffException(_(u"Invalid AIFF file"))

        total_size = aiff_header.aiff_size - 4
        while (total_size > 0):
            chunk_header = self.CHUNK_HEADER.parse_stream(f)
            total_size -= 8
            yield (chunk_header.chunk_id,
                   chunk_header.chunk_length,
                   __capped_stream_reader__(f,chunk_header.chunk_length))
            total_size -= chunk_header.chunk_length
        f.close()

    def get_metadata(self):
        for (chunk_id,chunk_length,chunk_offset) in self.chunks():
            if (chunk_id == 'ID3 '):
                f = open(self.filename,'rb')
                f.seek(chunk_offset,0)
                id3 = ID3v22Comment.parse(f)
                f.close()
                return id3
        else:
            return None

    def set_metadata(self, metadata):
        if (metadata is None):
            return

        import tempfile

        id3_chunk = ID3v22Comment.converted(metadata).build()

        new_aiff = tempfile.TemporaryFile()
        new_aiff.seek(12,0)

        id3_found = False
        for (chunk_id,chunk_length,chunk_file) in self.chunk_files():
            if (chunk_id != 'ID3 '):
                new_aiff.write(self.CHUNK_HEADER.build(
                        Con.Container(chunk_id=chunk_id,
                                      chunk_length=chunk_length)))
                transfer_data(chunk_file.read,new_aiff.write)
            else:
                new_aiff.write(self.CHUNK_HEADER.build(
                        Con.Container(chunk_id='ID3 ',
                                      chunk_length=len(id3_chunk))))
                new_aiff.write(id3_chunk)
                id3_found = True

        if (not id3_found):
            new_aiff.write(self.CHUNK_HEADER.build(
                    Con.Container(chunk_id='ID3 ',
                                  chunk_length=len(id3_chunk))))
            new_aiff.write(id3_chunk)

        header = Con.Container(
            aiff_id='FORM',
            aiff_size=new_aiff.tell() - 8,
            aiff_type='AIFF')
        new_aiff.seek(0,0)
        new_aiff.write(self.AIFF_HEADER.build(header))
        new_aiff.seek(0,0)
        f = open(self.filename,'wb')
        transfer_data(new_aiff.read,f.write)
        new_aiff.close()
        f.close()

    def delete_metadata(self):
        import tempfile

        new_aiff = tempfile.TemporaryFile()
        new_aiff.seek(12,0)

        for (chunk_id,chunk_length,chunk_file) in self.chunk_files():
            if (chunk_id != 'ID3 '):
                new_aiff.write(self.CHUNK_HEADER.build(
                        Con.Container(chunk_id=chunk_id,
                                      chunk_length=chunk_length)))
                transfer_data(chunk_file.read,new_aiff.write)

        header = Con.Container(
            aiff_id='FORM',
            aiff_size=new_aiff.tell() - 8,
            aiff_type='AIFF')
        new_aiff.seek(0,0)
        new_aiff.write(self.AIFF_HEADER.build(header))
        new_aiff.seek(0,0)
        f = open(self.filename,'wb')
        transfer_data(new_aiff.read,f.write)
        new_aiff.close()
        f.close()

    def to_pcm(self):
        for (chunk_id,chunk_length,chunk_offset) in self.chunks():
            if (chunk_id == 'SSND'):
                f = open(self.filename,'rb')
                f.seek(chunk_offset,0)
                alignment = self.SSND_ALIGN.parse_stream(f)
                #FIXME - handle different types of SSND alignment
                pcmreader = PCMReader(
                    __capped_stream_reader__(
                        f,chunk_length - self.SSND_ALIGN.sizeof()),
                    sample_rate=self.sample_rate(),
                    channels=self.channels(),
                    channel_mask=self.channel_mask(),
                    bits_per_sample=self.bits_per_sample(),
                    signed=True,
                    big_endian=True)
                if (self.channels() <= 2):
                    return pcmreader
                else:
                    #FIXME - handle undefined channel mask
                    standard_channel_mask = self.channel_mask()
                    aiff_channel_mask = AIFFChannelMask(self.channel_mask())
                    return ReorderedPCMReader(
                        pcmreader,
                        [aiff_channel_mask.channels().index(channel)
                         for channel in
                         standard_channel_mask.channels()])
        else:
            return PCMReaderError()

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        try:
            f = open(filename,'wb')
        except IOError:
            raise EncodingError(None)

        if (int(pcmreader.channel_mask) in
            (0x4,   #FC
             0x3,   #FL, FR
             0x7,   #FL, FR, FC
             0x33,  #FL, FR, BL, BR
             0x707) #FL, SL, FC, FR, SR, BC
            ):
            standard_channel_mask = ChannelMask(pcmreader.channel_mask)
            aiff_channel_mask = AIFFChannelMask(standard_channel_mask)
            pcmreader = ReorderedPCMReader(
                pcmreader,
                [standard_channel_mask.channels().index(channel)
                 for channel in aiff_channel_mask.channels()])
        else:
            #FIXME - support undefined channel assignments, if possible
            raise UnsupportedChannelMask()

        try:
            aiff_header = Con.Container(aiff_id='FORM',
                                        aiff_size=4,
                                        aiff_type='AIFF')

            comm_chunk = Con.Container(channels=pcmreader.channels,
                                       total_sample_frames=0,
                                       sample_size=pcmreader.bits_per_sample,
                                       sample_rate=float(pcmreader.sample_rate))

            ssnd_header = Con.Container(chunk_id='SSND',
                                        chunk_length=0)
            ssnd_alignment = Con.Container(offset=0,
                                           blocksize=0)

            #skip ahead to the start of the SSND chunk
            f.seek(cls.AIFF_HEADER.sizeof() +
                   cls.CHUNK_HEADER.sizeof() +
                   cls.COMM_CHUNK.sizeof() +
                   cls.CHUNK_HEADER.sizeof(),0)

            #write the SSND alignment info
            f.write(cls.SSND_ALIGN.build(ssnd_alignment))

            #write big-endian samples to SSND chunk from pcmreader
            framelist = pcmreader.read(BUFFER_SIZE)
            total_pcm_frames = 0
            while (len(framelist) > 0):
                f.write(framelist.to_bytes(True,True))
                total_pcm_frames += framelist.frames
                framelist = pcmreader.read(BUFFER_SIZE)
            total_size = f.tell()

            #return to the start of the file
            f.seek(0,0)

            #write AIFF header
            aiff_header.aiff_size = total_size - 8
            f.write(cls.AIFF_HEADER.build(aiff_header))

            #write COMM chunk
            comm_chunk.total_sample_frames = total_pcm_frames
            comm_chunk = cls.COMM_CHUNK.build(comm_chunk)
            f.write(cls.CHUNK_HEADER.build(Con.Container(
                        chunk_id='COMM',
                        chunk_length=len(comm_chunk))))
            f.write(comm_chunk)

            #write SSND chunk header
            f.write(cls.CHUNK_HEADER.build(Con.Container(
                        chunk_id='SSND',
                        chunk_length=(total_pcm_frames *
                                      (pcmreader.bits_per_sample / 8) *
                                      pcmreader.channels) +
                        cls.SSND_ALIGN.sizeof())))
            try:
                pcmreader.close()
            except DecodingError:
                raise EncodingError()
        finally:
            f.close()

        return cls(filename)

class AIFFChannelMask(ChannelMask):
    def __repr__(self):
        return "AIFFChannelMask(%s)" % \
            ",".join(["%s=%s" % (field,getattr(self,field))
                      for field in self.SPEAKER_TO_MASK.keys()
                      if (getattr(self,field))])

    def channels(self):
        count = len(self)
        if (count == 1):
            return ["front_center"]
        elif (count == 2):
            return ["front_left","front_right"]
        elif (count == 3):
            return ["front_left","front_right","front_center"]
        elif (count == 4):
            return ["front_left","front_right",
                    "back_left","back_right"]
        elif (count == 6):
            return ["front_left","side_left","front_center",
                    "front_right","side_right","back_center"]
        else:
            return []
