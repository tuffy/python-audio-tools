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

from audiotools import AudioFile,InvalidFile,PCMReader,ReorderedPCMReader,PCMConverter,Con,transfer_data,transfer_framelist_data,subprocess,BIN,cStringIO,open_files,os,ReplayGain,ignore_sigint,EncodingError,DecodingError,ChannelMask
from __vorbiscomment__ import *
import gettext

gettext.install("audiotools",unicode=True)

class OggStreamReader:
    OGGS = Con.Struct(
        "oggs",
        Con.Const(Con.String("magic_number",4),"OggS"),
        Con.Byte("version"),
        Con.Byte("header_type"),
        Con.SLInt64("granule_position"),
        Con.ULInt32("bitstream_serial_number"),
        Con.ULInt32("page_sequence_number"),
        Con.ULInt32("checksum"),
        Con.Byte("segments"),
        Con.MetaRepeater(lambda ctx: ctx["segments"],
                         Con.Byte("segment_lengths")))

    #stream is a file-like object with read() and close() methods
    def __init__(self, stream):
        self.stream = stream

    def close(self):
        self.stream.close()

    #an iterator which yields one fully-reassembled Ogg packet per pass
    def packets(self, from_beginning=True):
        if (from_beginning):
            self.stream.seek(0,0)

        segment = cStringIO.StringIO()

        while (True):
            try:
                page = OggStreamReader.OGGS.parse_stream(self.stream)

                for length in page.segment_lengths:
                    if (length == 255):
                        segment.write(self.stream.read(length))
                    else:
                        segment.write(self.stream.read(length))
                        yield segment.getvalue()
                        segment = cStringIO.StringIO()

            except Con.core.FieldError:
                break
            except Con.ConstError:
                break

    #an iterator which yields (Container,data string) tuples per pass
    #Container is parsed from OGGS
    #data string is a collection of segments as a string
    #(it may not be a complete packet)
    def pages(self, from_beginning=True):
        if (from_beginning):
            self.stream.seek(0,0)

        while (True):
            try:
                page = OggStreamReader.OGGS.parse_stream(self.stream)
                yield (page,self.stream.read(sum(page.segment_lengths)))
            except Con.core.FieldError:
                break
            except Con.ConstError:
                break


    #takes a page iterator (such as pages(), above)
    #returns a list of (Container,data string) tuples
    #which form a complete packet
    @classmethod
    def pages_to_packet(cls, pages_iter):
        packet = [pages_iter.next()]
        while (packet[-1][0].segment_lengths[-1] == 255):
            packet.append(pages_iter.next())
        return packet


    CRC_LOOKUP = (0x00000000,0x04c11db7,0x09823b6e,0x0d4326d9,
                  0x130476dc,0x17c56b6b,0x1a864db2,0x1e475005,
                  0x2608edb8,0x22c9f00f,0x2f8ad6d6,0x2b4bcb61,
                  0x350c9b64,0x31cd86d3,0x3c8ea00a,0x384fbdbd,
                  0x4c11db70,0x48d0c6c7,0x4593e01e,0x4152fda9,
                  0x5f15adac,0x5bd4b01b,0x569796c2,0x52568b75,
                  0x6a1936c8,0x6ed82b7f,0x639b0da6,0x675a1011,
                  0x791d4014,0x7ddc5da3,0x709f7b7a,0x745e66cd,
                  0x9823b6e0,0x9ce2ab57,0x91a18d8e,0x95609039,
                  0x8b27c03c,0x8fe6dd8b,0x82a5fb52,0x8664e6e5,
                  0xbe2b5b58,0xbaea46ef,0xb7a96036,0xb3687d81,
                  0xad2f2d84,0xa9ee3033,0xa4ad16ea,0xa06c0b5d,
                  0xd4326d90,0xd0f37027,0xddb056fe,0xd9714b49,
                  0xc7361b4c,0xc3f706fb,0xceb42022,0xca753d95,
                  0xf23a8028,0xf6fb9d9f,0xfbb8bb46,0xff79a6f1,
                  0xe13ef6f4,0xe5ffeb43,0xe8bccd9a,0xec7dd02d,
                  0x34867077,0x30476dc0,0x3d044b19,0x39c556ae,
                  0x278206ab,0x23431b1c,0x2e003dc5,0x2ac12072,
                  0x128e9dcf,0x164f8078,0x1b0ca6a1,0x1fcdbb16,
                  0x018aeb13,0x054bf6a4,0x0808d07d,0x0cc9cdca,
                  0x7897ab07,0x7c56b6b0,0x71159069,0x75d48dde,
                  0x6b93dddb,0x6f52c06c,0x6211e6b5,0x66d0fb02,
                  0x5e9f46bf,0x5a5e5b08,0x571d7dd1,0x53dc6066,
                  0x4d9b3063,0x495a2dd4,0x44190b0d,0x40d816ba,
                  0xaca5c697,0xa864db20,0xa527fdf9,0xa1e6e04e,
                  0xbfa1b04b,0xbb60adfc,0xb6238b25,0xb2e29692,
                  0x8aad2b2f,0x8e6c3698,0x832f1041,0x87ee0df6,
                  0x99a95df3,0x9d684044,0x902b669d,0x94ea7b2a,
                  0xe0b41de7,0xe4750050,0xe9362689,0xedf73b3e,
                  0xf3b06b3b,0xf771768c,0xfa325055,0xfef34de2,
                  0xc6bcf05f,0xc27dede8,0xcf3ecb31,0xcbffd686,
                  0xd5b88683,0xd1799b34,0xdc3abded,0xd8fba05a,
                  0x690ce0ee,0x6dcdfd59,0x608edb80,0x644fc637,
                  0x7a089632,0x7ec98b85,0x738aad5c,0x774bb0eb,
                  0x4f040d56,0x4bc510e1,0x46863638,0x42472b8f,
                  0x5c007b8a,0x58c1663d,0x558240e4,0x51435d53,
                  0x251d3b9e,0x21dc2629,0x2c9f00f0,0x285e1d47,
                  0x36194d42,0x32d850f5,0x3f9b762c,0x3b5a6b9b,
                  0x0315d626,0x07d4cb91,0x0a97ed48,0x0e56f0ff,
                  0x1011a0fa,0x14d0bd4d,0x19939b94,0x1d528623,
                  0xf12f560e,0xf5ee4bb9,0xf8ad6d60,0xfc6c70d7,
                  0xe22b20d2,0xe6ea3d65,0xeba91bbc,0xef68060b,
                  0xd727bbb6,0xd3e6a601,0xdea580d8,0xda649d6f,
                  0xc423cd6a,0xc0e2d0dd,0xcda1f604,0xc960ebb3,
                  0xbd3e8d7e,0xb9ff90c9,0xb4bcb610,0xb07daba7,
                  0xae3afba2,0xaafbe615,0xa7b8c0cc,0xa379dd7b,
                  0x9b3660c6,0x9ff77d71,0x92b45ba8,0x9675461f,
                  0x8832161a,0x8cf30bad,0x81b02d74,0x857130c3,
                  0x5d8a9099,0x594b8d2e,0x5408abf7,0x50c9b640,
                  0x4e8ee645,0x4a4ffbf2,0x470cdd2b,0x43cdc09c,
                  0x7b827d21,0x7f436096,0x7200464f,0x76c15bf8,
                  0x68860bfd,0x6c47164a,0x61043093,0x65c52d24,
                  0x119b4be9,0x155a565e,0x18197087,0x1cd86d30,
                  0x029f3d35,0x065e2082,0x0b1d065b,0x0fdc1bec,
                  0x3793a651,0x3352bbe6,0x3e119d3f,0x3ad08088,
                  0x2497d08d,0x2056cd3a,0x2d15ebe3,0x29d4f654,
                  0xc5a92679,0xc1683bce,0xcc2b1d17,0xc8ea00a0,
                  0xd6ad50a5,0xd26c4d12,0xdf2f6bcb,0xdbee767c,
                  0xe3a1cbc1,0xe760d676,0xea23f0af,0xeee2ed18,
                  0xf0a5bd1d,0xf464a0aa,0xf9278673,0xfde69bc4,
                  0x89b8fd09,0x8d79e0be,0x803ac667,0x84fbdbd0,
                  0x9abc8bd5,0x9e7d9662,0x933eb0bb,0x97ffad0c,
                  0xafb010b1,0xab710d06,0xa6322bdf,0xa2f33668,
                  0xbcb4666d,0xb8757bda,0xb5365d03,0xb1f740b4)

    #page_header is a Container object parsed through OGGS, above
    #page_data is a string of data contained by the page
    #returns an integer of the page's checksum
    @classmethod
    def calculate_ogg_checksum(cls, page_header, page_data):
        old_checksum = page_header.checksum
        try:
            page_header.checksum = 0
            sum = 0
            for c in cls.OGGS.build(page_header) + page_data:
                sum = ((sum << 8) ^ \
                       cls.CRC_LOOKUP[((sum >> 24) & 0xFF)^ ord(c)]) \
                       & 0xFFFFFFFF
            return sum
        finally:
            page_header.checksum = old_checksum


class OggStreamWriter:
    #stream is a file-like object with write() and close() methods
    def __init__(self, stream):
        self.stream = stream

    def close(self):
        self.stream.close()

    #page_header is an OGGS-generated Container with all of the
    #fields properly set
    #page_data is a string containing all of the page's segment data
    #this builds the entire page and sends it to stream
    def write_page(self, page_header, page_data):
        self.stream.write(OggStreamReader.OGGS.build(page_header))
        self.stream.write(page_data)

    #takes serial_number, granule_position and starting_sequence_number
    #integers and a packet_data string
    #returns a list of (page_header,page_data) tuples containing
    #all of the Ogg pages necessary to contain the packet
    @classmethod
    def build_pages(cls, granule_position, serial_number,
                    starting_sequence_number, packet_data,
                    header_type=0):

        page = Con.Container(magic_number = 'OggS',
                             version = 0,
                             header_type = header_type,
                             granule_position = granule_position,
                             bitstream_serial_number = serial_number,
                             page_sequence_number = starting_sequence_number,
                             checksum = 0)

        if (len(packet_data) == 0):
            #an empty Ogg page, but possibly a continuation

            page.segments = 0
            page.segment_lengths = []
            page.checksum = OggStreamReader.calculate_ogg_checksum(
                page,packet_data)
            return [(page,"")]
        if (len(packet_data) > (255 * 255)):
            #if we need more than one Ogg page to store the packet,
            #handle that case recursively

            page.segments = 255
            page.segment_lengths = [255] * 255
            page.checksum = OggStreamReader.calculate_ogg_checksum(
                page,packet_data[0:255 * 255])

            return [(page,packet_data[0:255 * 255])] + \
                   cls.build_pages(granule_position,
                                   serial_number,
                                   starting_sequence_number + 1,
                                   packet_data[255*255:],
                                   header_type)
        elif (len(packet_data) == (255 * 255)):
            #we need two Ogg pages, one of which is empty

            return cls.build_pages(granule_position,
                                   serial_number,
                                   starting_sequence_number,
                                   packet_data,
                                   header_type) + \
                   cls.build_pages(granule_position,
                                   serial_number,
                                   starting_sequence_number + 1,
                                   "",
                                   header_type)
        else:
            #we just need one Ogg page

            page.segments = len(packet_data) / 255
            if ((len(packet_data) % 255) > 0):
                page.segments += 1

            page.segment_lengths = [255] * (len(packet_data) / 255)
            if ((len(packet_data) % 255) > 0):
                page.segment_lengths += [len(packet_data) % 255]

            page.checksum = OggStreamReader.calculate_ogg_checksum(
                page,packet_data)
            return [(page,packet_data)]


#######################
#Vorbis File
#######################

class VorbisAudio(AudioFile):
    SUFFIX = "ogg"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "3"
    COMPRESSION_MODES = tuple([str(i) for i in range(0,11)])
    BINARIES = ("oggenc","oggdec","vorbiscomment")

    OGG_IDENTIFICATION = Con.Struct(
        "ogg_id",
        Con.ULInt32("vorbis_version"),
        Con.Byte("channels"),
        Con.ULInt32("sample_rate"),
        Con.ULInt32("bitrate_maximum"),
        Con.ULInt32("bitrate_nominal"),
        Con.ULInt32("bitrate_minimum"),
        Con.Embed(Con.BitStruct("flags",
                                Con.Bits("blocksize_0",
                                         4),
                                Con.Bits("blocksize_1",
                                         4))),
        Con.Byte("framing"))

    COMMENT_HEADER = Con.Struct(
        "comment_header",
        Con.Byte("packet_type"),
        Con.String("vorbis",6))

    def __init__(self, filename):
        AudioFile.__init__(self, filename)
        self.__read_metadata__()

    @classmethod
    def is_type(cls, file):
        header = file.read(0x23)

        return (header.startswith('OggS') and
                header[0x1C:0x23] == '\x01vorbis')

    def __read_metadata__(self):
        f = OggStreamReader(file(self.filename,"rb"))
        packets = f.packets()

        try:
            #we'll assume this Vorbis file isn't interleaved
            #with any other Ogg stream

            #the Identification packet comes first
            id_packet = packets.next()
            header = VorbisAudio.COMMENT_HEADER.parse(
                id_packet[0:VorbisAudio.COMMENT_HEADER.sizeof()])
            if ((header.packet_type == 0x01) and
                (header.vorbis == 'vorbis')):
                identification = VorbisAudio.OGG_IDENTIFICATION.parse(
                    id_packet[VorbisAudio.COMMENT_HEADER.sizeof():])
                self.__sample_rate__ = identification.sample_rate
                self.__channels__ = identification.channels
            else:
                raise InvalidFile(_(u'First packet is not Vorbis'))

            #the Comment packet comes next
            comment_packet = packets.next()
            header = VorbisAudio.COMMENT_HEADER.parse(
                comment_packet[0:VorbisAudio.COMMENT_HEADER.sizeof()])
            if ((header.packet_type == 0x03) and
                (header.vorbis == 'vorbis')):
                self.comment = VorbisComment.VORBIS_COMMENT.parse(
                    comment_packet[VorbisAudio.COMMENT_HEADER.sizeof():])

        finally:
            del(packets); f.close(); del(f)

    def lossless(self):
        return False

    def bits_per_sample(self):
        return 16

    def channels(self):
        return self.__channels__

    def channel_mask(self):
        if (self.channels() == 1):
            return ChannelMask.from_fields(
                front_center=True)
        elif (self.channels() == 2):
            return ChannelMask.from_fields(
                front_left=True,front_right=True)
        elif (self.channels() == 3):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,
                front_center=True)
        elif (self.channels() == 4):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,
                back_left=True,back_right=True)
        elif (self.channels() == 5):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,
                front_center=True,
                back_left=True,back_right=True)
        elif (self.channels() == 6):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,
                front_center=True,
                back_left=True,back_right=True,
                low_frequency=True)
        elif (self.channels() == 7):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,
                front_center=True,
                side_left=True,side_right=True,
                rear_center=True,low_frequency=True)
        elif (self.channels() == 8):
            return ChannelMask.from_fields(
                front_left=True,front_right=True,
                side_left=True,side_right=True,
                back_left=True,back_right=True,
                front_center=True,low_frequency=True)
        else:
            raise ValueError("undefined channel mask")

    def total_frames(self):
        pcm_samples = 0
        f = file(self.filename,"rb")
        try:
            while (True):
                try:
                    page = OggStreamReader.OGGS.parse_stream(f)
                    pcm_samples = page.granule_position
                    f.seek(sum(page.segment_lengths),1)
                except Con.core.FieldError:
                    break
                except Con.ConstError:
                    break

            return pcm_samples
        finally:
            f.close()

    def sample_rate(self):
        return self.__sample_rate__

    def to_pcm(self):
        sub = subprocess.Popen([BIN['oggdec'],'-Q',
                                '-b',str(16),
                                '-e',str(0),
                                '-s',str(1),
                                '-R',
                                '-o','-',
                                self.filename],
                               stdout=subprocess.PIPE)

        pcmreader = PCMReader(sub.stdout,
                              sample_rate = self.sample_rate(),
                              channels = self.channels(),
                              channel_mask = self.channel_mask(),
                              bits_per_sample = self.bits_per_sample(),
                              process=sub)

        if (self.channels() <= 2):
            return pcmreader
        elif (self.channels() <= 8):
            #these mappings transform Vorbis order into ChannelMask order
            return ReorderedPCMReader(pcmreader,
                                      {
                    #3 - front_left, front_center, front_right
                    3:[0,2,1],

                    #4 - front_left, front_right, back_left, back_right
                    4:[0,1,2,3],

                    #5 - FL, FC, FR, BL, BR
                    5:[0,2,1,3,4],

                    #6 - FL, FC, FR, BL, BR, LFE
                    6:[0,2,1,5,3,4],

                    #7 - FL, FC, FR, SL, SR, BC, LFE
                    7:[0,2,1,6,5,3,4],

                    #8 - FL, FC, FR, SL, SR, BL, BR, LFE
                    8:[0,2,1,7,5,6,3,4]}[self.channels()])
        else:
            raise ValueError("unsupported channel count")

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.bits_per_sample not in (8,16,24)):
            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=pcmreader.sample_rate,
                channels=pcmreader.channels,
                bits_per_sample=min(pcmreader.bits_per_sample,16))

        devnull = file(os.devnull,'ab')

        sub = subprocess.Popen([BIN['oggenc'],'-Q',
                                '-r',
                                '-B',str(pcmreader.bits_per_sample),
                                '-C',str(pcmreader.channels),
                                '-R',str(pcmreader.sample_rate),
                                '--raw-endianness',str(0),
                                '-q',compression,
                                '-o',filename,'-'],
                               stdin=subprocess.PIPE,
                               stdout=devnull,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)

        if (pcmreader.channels <= 2):
            transfer_framelist_data(pcmreader,sub.stdin.write)
        elif (pcmreader.channels <= 8):
            channel_mask = int(pcmreader.channel_mask)
            if (channel_mask ==
                int(ChannelMask.from_fields(front_left=True,
                                            front_right=True,
                                            front_center=True))):
                channel_map = [0,2,1]
            elif (channel_mask ==
                int(ChannelMask.from_fields(front_left=True,
                                            front_right=True,
                                            back_left=True,
                                            back_right=True))):
                channel_map = [0,1,2,3]
            elif (channel_mask ==
                int(ChannelMask.from_fields(front_left=True,
                                            front_right=True,
                                            front_center=True,
                                            back_left=True,
                                            back_right=True))):
                channel_map = [0,2,1,3,4]
            elif (channel_mask ==
                int(ChannelMask.from_fields(front_left=True,
                                            front_right=True,
                                            front_center=True,
                                            back_left=True,
                                            back_right=True,
                                            low_frequency=True))):
                channel_map = [0,2,1,5,3,4]
            elif (channel_mask ==
                int(ChannelMask.from_fields(front_left=True,
                                            front_right=True,
                                            front_center=True,
                                            side_left=True,
                                            side_right=True,
                                            back_center=True,
                                            low_frequency=True))):
                channel_map = [0,2,1,6,5,3,4]
            elif (channel_mask ==
                int(ChannelMask.from_fields(front_left=True,
                                            front_right=True,
                                            front_center=True,
                                            side_left=True,
                                            side_right=True,
                                            back_left=True,
                                            back_right=True,
                                            low_frequency=True))):
                channel_map = [0,2,1,7,5,6,3,4]
            else:
                raise UnsupportedChannelMask()

            print "Using channel map %s" % (channel_map)
            transfer_framelist_data(ReorderedPCMReader(pcmreader),
                                    sub.stdin.write)
        else:
          raise UnsupportedChannelMask()


        try:
            pcmreader.close()
        except DecodingError:
            raise EncodingError()
        sub.stdin.close()

        devnull.close()

        if (sub.wait() == 0):
            return VorbisAudio(filename)
        else:
            raise EncodingError(BIN['oggenc'])

    def set_metadata(self, metadata):
        metadata = VorbisComment.converted(metadata)

        if (metadata is None): return

        reader = OggStreamReader(file(self.filename,'rb'))
        new_file = cStringIO.StringIO()
        writer = OggStreamWriter(new_file)
        current_sequence_number = 0

        pages = reader.pages()

        #transfer our old header
        #this must always be the first packet and the first page
        (header_page,header_data) = pages.next()
        writer.write_page(header_page,header_data)
        current_sequence_number += 1

        #grab the current "comment" and "setup headers" packets
        #these may take one or more pages,
        #but will always end on a page boundary
        del(pages)
        packets = reader.packets(from_beginning=False)

        comment_packet = packets.next()
        headers_packet = packets.next()

        #write the pages for our new "comment" packet
        for (page,data) in OggStreamWriter.build_pages(
            0,
            header_page.bitstream_serial_number,
            current_sequence_number,
            VorbisAudio.COMMENT_HEADER.build(Con.Container(
                    packet_type=3,
                    vorbis='vorbis')) + metadata.build()):
            writer.write_page(page,data)
            current_sequence_number += 1

        #write the pages for the old "setup headers" packet
        for (page,data) in OggStreamWriter.build_pages(
            0,
            header_page.bitstream_serial_number,
            current_sequence_number,
            headers_packet):
            writer.write_page(page,data)
            current_sequence_number += 1

        #write the rest of the pages, re-sequenced and re-checksummed
        del(packets)
        pages = reader.pages(from_beginning=False)

        for (i,(page,data)) in enumerate(pages):
            page.page_sequence_number = i + current_sequence_number
            page.checksum = OggStreamReader.calculate_ogg_checksum(page,data)
            writer.write_page(page,data)

        reader.close()

        #re-write the file with our new data in "new_file"
        f = file(self.filename,"wb")
        f.write(new_file.getvalue())
        f.close()
        writer.close()

        self.__read_metadata__()

    def get_metadata(self):
        self.__read_metadata__()
        data = {}
        for pair in self.comment.value:
            try:
                (key,value) = pair.split('=',1)
                data.setdefault(key,[]).append(value.decode('utf-8'))
            except ValueError:
                continue

        return VorbisComment(data)

    def delete_metadata(self):
        self.set_metadata(MetaData())

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]

        if ((len(track_names) > 0) and
            BIN.can_execute(BIN['vorbisgain'])):
            devnull = file(os.devnull,'ab')

            sub = subprocess.Popen([BIN['vorbisgain'],
                                    '-q','-a'] + track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()

    @classmethod
    def can_add_replay_gain(cls):
        return BIN.can_execute(BIN['vorbisgain'])

    @classmethod
    def lossless_replay_gain(cls):
        return True

    def replay_gain(self):
        vorbis_metadata = self.get_metadata()

        if (set(['REPLAYGAIN_TRACK_PEAK', 'REPLAYGAIN_TRACK_GAIN',
                 'REPLAYGAIN_ALBUM_PEAK', 'REPLAYGAIN_ALBUM_GAIN']).issubset(
                vorbis_metadata.keys())):  #we have ReplayGain data
            try:
                return ReplayGain(
                    vorbis_metadata['REPLAYGAIN_TRACK_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_TRACK_PEAK'][0],
                    vorbis_metadata['REPLAYGAIN_ALBUM_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_ALBUM_PEAK'][0])
            except ValueError:
                return None
        else:
            return None

class VorbisChannelMask(ChannelMask):
    def __repr__(self):
        return "VorbisChannelMask(%s)" % \
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
            return ["front_left","front_center","front_right"]
        elif (count == 4):
            return ["front_left","front_right",
                    "back_left","back_right"]
        elif (count == 5):
            return ["front_left","front_center","front_right",
                    "back_left","back_right"]
        elif (count == 6):
            return ["front_left","front_center","front_right",
                    "back_left","back_right","low_frequency"]
        elif (count == 7):
            return ["front_left","front_center","front_right",
                    "side_left","side_right","back_center",
                    "low_frequency"]
        elif (count == 8):
            return ["front_left","front_center","front_right",
                    "side_left","side_right",
                    "back_left","back_right","low_frequency"]
        else:
            return []
