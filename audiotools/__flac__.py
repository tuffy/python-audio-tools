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


from audiotools import AudioFile,InvalidFile,PCMReader,Con,transfer_data,subprocess,BIN,BUFFER_SIZE,cStringIO,os,open_files,Image,ImageMetaData,sys,WaveAudio
from __vorbiscomment__ import *
from __id3__ import ID3v2Comment
from __vorbis__ import OggStreamReader,OggStreamWriter


#######################
#FLAC
#######################

class FlacException(InvalidFile): pass

class FlacMetaDataBlock:
    #type is an int
    #data is a string of metadata
    def __init__(self, type, data):
        self.type = type
        self.data = data

    #returns the entire metadata block as a string, including the header
    def build_block(self, last=0):
        return FlacAudio.METADATA_BLOCK_HEADER.build(
            Con.Container(last_block=last,
                          block_type=self.type,
                          block_length=len(self.data))) + self.data

class FlacMetaData(ImageMetaData,MetaData):
    #blocks is a list of FlacMetaDataBlock objects
    #these get converted internally into MetaData/ImageMetaData fields
    def __init__(self, blocks):
        #IMPORTANT!
        #Externally converted FlacMetaData likely won't have a valid STREAMINFO
        #so set_metadata() must override this value with the current
        #FLAC's streaminfo before setting the metadata blocks.
        self.__dict__['streaminfo'] = None

        #Don't use an external SEEKTABLE, either.
        self.__dict__['seektable'] = None
        
        self.__dict__['vorbis_comment'] = None
        self.__dict__['cuesheet'] = None
        image_blocks = []
        self.__dict__['extra_blocks'] = []
        
        for block in blocks:
            if ((block.type == 0) and (self.streaminfo is None)):
                #only one STREAMINFO allowed
                self.__dict__['streaminfo'] = block
            elif ((block.type == 4) and (self.vorbis_comment is None)):
                #only one VORBIS_COMMENT allowed
                comments = {}
                
                for comment in FlacVorbisComment.VORBIS_COMMENT.parse(block.data).value:
                    try:
                        key = comment[0:comment.index("=")].upper()
                        value = comment[comment.index("=") + 1:].decode('utf-8')
                        comments.setdefault(key,[]).append(value)
                    except ValueError:
                        pass
                
                self.__dict__['vorbis_comment'] = FlacVorbisComment(comments)
            elif ((block.type == 5) and (self.cuesheet is None)):
                #only one CUESHEET allowed
                self.__dict__['cuesheet'] = block
            elif ((block.type == 3) and (self.seektable is None)):
                #only one SEEKTABLE allowed
                self.__dict__['seektable'] = block
            elif (block.type == 6):
                #multiple PICTURE blocks are ok
                image = FlacAudio.PICTURE_COMMENT.parse(block.data)
                
                image_blocks.append(FlacPictureComment(
                    type=image.type,
                    mime_type=image.mime_type.decode('ascii','replace'),
                    description=image.description.decode('utf-8','replace'),
                    width=image.width,
                    height=image.height,
                    color_depth=image.color_depth,
                    color_count=image.color_count,
                    data=image.data))
            elif (block.type != 1):
                #everything but the padding is stored as extra
                self.__dict__['extra_blocks'].append(block)

        if (self.vorbis_comment is None):
            self.vorbis_comment = FlacVorbisComment({})

        MetaData.__init__(self,
                          track_name=self.vorbis_comment.track_name,
                          track_number=self.vorbis_comment.track_number,
                          album_name=self.vorbis_comment.album_name,
                          artist_name=self.vorbis_comment.artist_name,
                          performer_name=self.vorbis_comment.performer_name,
                          copyright=self.vorbis_comment.copyright,
                          year=self.vorbis_comment.year)
        ImageMetaData.__init__(self,image_blocks)

    def __comment_name__(self):
        return u'FLAC'

    def __comment_pairs__(self):
        return self.vorbis_comment.__comment_pairs__()

    def __setattr__(self, key, value):
        self.__dict__[key] = value
        setattr(self.vorbis_comment, key, value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,FlacMetaData))):
            return metadata
        else:
            if (isinstance(metadata,ImageMetaData)):
                return FlacMetaData([
                    FlacMetaDataBlock(
                    type=4,
                    data=FlacVorbisComment.converted(metadata).build())] + \
                                    [
                    FlacMetaDataBlock(
                      type=6,
                      data=FlacPictureComment.converted(image).build())
                      for image in metadata.images()])
            else:
                return FlacMetaData([
                    FlacMetaDataBlock(
                    type=4,
                    data=FlacVorbisComment.converted(metadata).build())])

    def add_image(self, image):
        ImageMetaData.add_image(self,FlacPictureComment.converted(image))

    #returns an iterator over all the current blocks as
    #FlacMetaDataBlock-compatible objects and without padding at the end
    def metadata_blocks(self):
        yield self.streaminfo
        yield self.vorbis_comment
        
        if (self.seektable is not None):
            yield self.seektable
        
        if (self.cuesheet is not None):
            yield self.cuesheet

        for image in self.images():
            yield image

        for extra in self.extra_blocks:
            yield extra


    def build(self):
        return "".join(
            [block.build_block() for block in self.metadata_blocks()]) + \
            FlacMetaDataBlock(type=1,
                              data=chr(0) * 4096).build_block(last=1)
            


#a slight variation of VorbisComment without the framing bit
#and with a build_block() method
class FlacVorbisComment(VorbisComment):
    VORBIS_COMMENT = Con.Struct("vorbis_comment",
                                Con.PascalString("vendor_string",
                                                 length_field=Con.ULInt32("length")),
                                Con.PrefixedArray(
        length_field=Con.ULInt32("length"),
        subcon=Con.PascalString("value",
                                length_field=Con.ULInt32("length"))))
    
    def build_block(self, last=0):
        block = self.build()
        return FlacAudio.METADATA_BLOCK_HEADER.build(
            Con.Container(last_block=last,
                          block_type=4,
                          block_length=len(block))) + block

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,FlacVorbisComment))):
            return metadata
        elif (isinstance(metadata,FlacMetaData)):
            return metadata.vorbis_comment
        elif (isinstance(metadata,VorbisComment)):
            return FlacVorbisComment(metadata)
        else:
            values = {}
            for key in cls.ATTRIBUTE_MAP.keys():
                if (getattr(metadata,key) != u""):
                    values[cls.ATTRIBUTE_MAP[key]] = \
                        [unicode(getattr(metadata,key))]

            return FlacVorbisComment(values)
  

#this is a container for FLAC's PICTURE metadata blocks
#type, width, height, color_depth and color_count are ints
#mime_type and description are unicode strings
#data is a string
class FlacPictureComment(Image):
    def __init__(self, type, mime_type, description,
                 width, height, color_depth, color_count, data):
        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=width,
                       height=height,
                       color_depth=color_depth,
                       color_count=color_count,
                       description=description,
                       type={3:0,4:1,5:2,6:3}.get(type,4))
        self.flac_type = type

    #takes an Image object
    #returns a FlacPictureComment
    @classmethod
    def converted(cls, image):
        return FlacPictureComment(
            type={0:3,1:4,2:5,3:6}.get(image.type,0),
            mime_type=image.mime_type,
            description=image.description,
            width=image.width,
            height=image.height,
            color_depth=image.color_depth,
            color_count=image.color_count,
            data=image.data)

    def type_string(self):
        return {0:"Other",
                1:"32x32 pixels 'file icon' (PNG only)",
                2:"Other file icon",
                3:"Cover (front)",
                4:"Cover (back)",
                5:"Leaflet page",
                6:"Media (e.g. label side of CD)",
                7:"Lead artist/lead performer/soloist",
                8:"Artist / Performer",
                9:"Conductor",
                10:"Band / Orchestra",
                11:"Composer",
                12:"Lyricist / Text writer",
                13:"Recording Location",
                14:"During recording",
                15:"During performance",
                16:"Movie/Video screen capture",
                17:"A bright coloured fish",
                18:"Illustration",
                19:"Band/Artist logotype",
                20:"Publisher/Studio logotype"}.get(self.flac_type,"Other")


    def __repr__(self):
        return "FlacPictureComment(type=%s,mime_type=%s,description=%s,width=%s,height=%s,...)" % \
               (repr(self.flac_type),repr(self.mime_type),
                repr(self.description),
                repr(self.width),repr(self.height))

    def build(self):
        return FlacAudio.PICTURE_COMMENT.build(
            Con.Container(type=self.flac_type,
                          mime_type=self.mime_type.encode('ascii'),
                          description=self.description.encode('utf-8'),
                          width=self.width,
                          height=self.height,
                          color_depth=self.color_depth,
                          color_count=self.color_count,
                          data=self.data))

    def build_block(self,last=0):
        block = self.build()
        return FlacAudio.METADATA_BLOCK_HEADER.build(
            Con.Container(last_block=last,
                          block_type=6,
                          block_length=len(block))) + block


class FlacAudio(AudioFile):
    SUFFIX = "flac"
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str,range(0,9)))
    BINARIES = ("flac","metaflac")
    
    
    METADATA_BLOCK_HEADER = Con.BitStruct("metadata_block_header",
                                          Con.Bit("last_block"),
                                          Con.Bits("block_type",7),
                                          Con.Bits("block_length",24))
    
    STREAMINFO = Con.Struct("flac_streaminfo",
                                 Con.UBInt16("minimum_blocksize"),
                                 Con.UBInt16("maximum_blocksize"),
                                 Con.Embed(Con.BitStruct("flags",
                                   Con.Bits("minimum_framesize",24),
                                   Con.Bits("maximum_framesize",24),
                                   Con.Bits("samplerate",20),
                                   Con.Bits("channels",3),
                                   Con.Bits("bits_per_sample",5),
                                   Con.Bits("total_samples",36))),
                                 Con.StrictRepeater(16,Con.Byte("md5")))

    PICTURE_COMMENT = Con.Struct("picture_comment",
                                 Con.UBInt32("type"),
                                 Con.PascalString("mime_type",
                                                  length_field=Con.UBInt32("mime_type_length")),
                                 Con.PascalString("description",
                                                  length_field=Con.UBInt32("description_length")),
                                 Con.UBInt32("width"),
                                 Con.UBInt32("height"),
                                 Con.UBInt32("color_depth"),
                                 Con.UBInt32("color_count"),
                                 Con.PascalString("data",
                                                  length_field=Con.UBInt32("data_length")))

    CUESHEET = Con.Struct("flac_cuesheet",
  Con.StrictRepeater(128,Con.Byte("catalog_number")),
  Con.UBInt64("lead_in_samples"),
  Con.Embed(Con.BitStruct("flags",
                          Con.Bits("is_cd",1),
                          Con.Bits("reserved1",7))),
  Con.StrictRepeater(258,Con.Byte("reserved2")),
  Con.PrefixedArray(
    length_field=Con.Byte("count"),
    subcon=Con.Struct("cuesheet_tracks",
      Con.UBInt64("track_offset"),
      Con.Byte("track_number"),
      Con.StrictRepeater(12,Con.Byte("ISRC")),
      Con.Embed(Con.BitStruct("sub_flags",
                              Con.Flag("track_type"),
                              Con.Flag("pre_emphasis"),
                              Con.Bits("reserved1",6))),
      Con.StrictRepeater(13,Con.Byte("reserved2")),
      Con.PrefixedArray(
        length_field=Con.Byte("count"),
        subcon=Con.Struct("cuesheet_track_index",
          Con.UBInt64("offset"),
          Con.Byte("point_number"),
          Con.StrictRepeater(3,Con.Byte("reserved")))
            ))
         ))
    
    def __init__(self, filename):
        AudioFile.__init__(self, filename)
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_samples__ = 0

        self.__read_streaminfo__()

    @classmethod
    def is_type(cls, file):
        if (file.read(4) == 'fLaC'):
            return True
        else:
            #I've seen FLAC files tagged with ID3v2 comments.
            #Though the official flac binaries grudgingly accept these,
            #such tags are unnecessary and outside the specification
            #so I will encourage people to remove them.
            
            file.seek(-4,1)
            ID3v2Comment.skip(file)
            if (file.read(4) == 'fLaC'):
                if (hasattr(file,"name")):
                    print >>sys.stderr,"*** %s: ID3v2 tag found at start of FLAC file.  Please remove." % (file.name)
                else:
                    print >>sys.stderr,"*** ID3v2 tag found at start of FLAC file.  Please remove."
            return False

    def lossless(self):
        return True

    @classmethod
    def __help_output__(cls):
        help_data = cStringIO.StringIO()
        sub = subprocess.Popen([BIN['flac'],'--help'],
                               stdout=subprocess.PIPE)
        transfer_data(sub.stdout.read,help_data.write)
        sub.wait()
        return help_data.getvalue()

    @classmethod
    def supports_foreign_riff_chunks(cls):
        return '--keep-foreign-metadata' in cls.__help_output__()

    #returns a MetaData-compatible VorbisComment for this FLAC files
    def get_metadata(self):
        f = file(self.filename,'rb')
        try:
            if (f.read(4) != 'fLaC'):
                raise FlacException('invalid FLAC file')
            
            blocks = []

            while (True):
                header = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(f)
                blocks.append(FlacMetaDataBlock(
                    type=header.block_type,
                    data=f.read(header.block_length)))
                if (header.last_block == 1):
                    break

            return FlacMetaData(blocks)
        finally:
            f.close()

    def set_metadata(self, metadata):
        import tempfile
        
        metadata = FlacMetaData.converted(metadata)
        
        if (metadata == None): return

        #port over the old STREAMINFO and SEEKTABLE blocks
        old_metadata = self.get_metadata()
        old_streaminfo = old_metadata.streaminfo
        old_seektable = old_metadata.seektable
        metadata.streaminfo = old_streaminfo
        if (old_seektable is not None):
            metadata.seektable = old_seektable

        stream = file(self.filename,'rb')

        if (stream.read(4) != 'fLaC'):
            raise FlacException('invalid FLAC file')
        
        block = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(stream)
        while (block.last_block == 0):
            stream.seek(block.block_length,1)
            block = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(stream)
        stream.seek(block.block_length,1)

        file_data = tempfile.TemporaryFile()
        transfer_data(stream.read,file_data.write)
        file_data.seek(0,0)

        stream = file(self.filename,'wb')
        stream.write('fLaC')
        stream.write(metadata.build())
        transfer_data(file_data.read,stream.write)
        file_data.close()
        stream.close()


    @classmethod
    def __read_flac_header__(cls, flacfile):
        p = FlacAudio.METADATA_BLOCK_HEADER.parse(flacfile.read(4))
        return (p.last_block, p.block_type, p.block_length)
    
    def to_pcm(self):
        sub = subprocess.Popen([BIN['flac'],"-s","-d","-c",
                                "--force-raw-format",
                                "--endian=little",
                                "--sign=signed",
                                self.filename],
                               stdout=subprocess.PIPE)
        return PCMReader(sub.stdout,
                         sample_rate=self.__samplerate__,
                         channels=self.__channels__,
                         bits_per_sample=self.__bitspersample__,
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="8"):
        SUBSTREAM_SAMPLE_RATES = frozenset([
                8000, 16000,22050,24000,32000,
                44100,48000,96000])
        SUBSTREAM_BITS = frozenset([8,12,16,20,24])

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if ((pcmreader.sample_rate in SUBSTREAM_SAMPLE_RATES) and
            (pcmreader.bits_per_sample in SUBSTREAM_BITS)):
            lax = []
        else:
            lax = ["--lax"]

        sub = subprocess.Popen([BIN['flac']] + lax + \
                               ["-s","-f","-%s" % (compression),
                                "-V",
                                "--endian=little",
                                "--channels=%d" % (pcmreader.channels),
                                "--bps=%d" % (pcmreader.bits_per_sample),
                                "--sample-rate=%d" % (pcmreader.sample_rate),
                                "--sign=signed",
                                "--force-raw-format",
                                "-o",filename,"-"],
                               stdin=subprocess.PIPE)

        transfer_data(pcmreader.read,sub.stdin.write)
        sub.stdin.close()
        pcmreader.close()
        sub.wait()

        sub = subprocess.Popen([BIN['metaflac'],
                                "--add-seekpoint=10s",
                                filename])
        sub.wait()

        return FlacAudio(filename)

    def __has_foreign_metadata__(self):
        return 'riff' in [block.data[0:4] for block in
                          self.get_metadata().extra_blocks
                          if block.type == 2]

    def to_wave(self, wave_filename):
        if (self.__has_foreign_metadata__() and
            ('--keep-foreign-metadata' in FlacAudio.__help_output__())):
            foreign_metadata = ['--keep-foreign-metadata']
        else:
            foreign_metadata = []
        
        sub = subprocess.Popen([BIN['flac'],"-s","-f"] + \
                               foreign_metadata + \
                               ["-d","-o",wave_filename,
                                self.filename])

        sub.wait()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (('--keep-foreign-metadata' in FlacAudio.__help_output__()) and
            (frozenset(WaveAudio(wave_filename).chunk_ids()) != \
             frozenset(['fmt ','data']))):
            foreign_metadata = ['--keep-foreign-metadata']
        else:
            foreign_metadata = []

        sub = subprocess.Popen([BIN['flac']] + \
                               ["-s","-f","-%s" % (compression),
                                "-V","--lax"] + \
                               foreign_metadata + \
                               ["-o",filename,wave_filename])
        sub.wait()
        return FlacAudio(filename)

    def bits_per_sample(self):
        return self.__bitspersample__

    def channels(self):
        return self.__channels__

    def total_samples(self):
        return self.__total_samples__

    def sample_rate(self):
        return self.__samplerate__

    def __read_streaminfo__(self):
        f = file(self.filename,"rb")
        if (f.read(4) != "fLaC"):
            raise FlacException("Not a FLAC file")

        (stop,header_type,length) = FlacAudio.__read_flac_header__(f)
        if (header_type != 0):
            raise FlacException("STREAMINFO not first metadata block")
    
        p = FlacAudio.STREAMINFO.parse(f.read(length))

        md5sum = "".join(["%.2X" % (x) for x in p.md5]).lower()

        self.__samplerate__ = p.samplerate
        self.__channels__ = p.channels + 1
        self.__bitspersample__ = p.bits_per_sample + 1
        self.__total_samples__ = p.total_samples
        self.__md5__ = "".join([chr(c) for c in p.md5])
        f.close()

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       (isinstance(track,cls) and
                        (track.channels() == 2) and
                        (track.bits_per_sample() == 16) and
                        ((track.sample_rate() == 44100) or
                         (track.sample_rate() == 48000)))]
        
        if ((len(track_names) > 0) and (BIN.can_execute(BIN['metaflac']))):
            subprocess.call([BIN['metaflac'],'--add-replay-gain'] + \
                            track_names)

    @classmethod
    def can_add_replay_gain(cls):
        return BIN.can_execute(BIN['metaflac'])

    def __eq__(self, audiofile):
        if (isinstance(audiofile,FlacAudio)):
            return self.__md5__ == audiofile.__md5__
        elif (isinstance(audiofile,AudioFile)):
            import md5
            
            p = audiofile.to_pcm()
            m = md5.new()
            s = p.read(BUFFER_SIZE)
            while (len(s) > 0):
                m.update(s)
                s = p.read(BUFFER_SIZE)
            p.close()
            return m.digest() == self.__md5__
        else:
            return False
    
    #returns a list of (track_number,"start.x-stop.y") tuples
    #for use by the --cue FLAC decoding option
    #track_number starts from 0, for consistency
    def cuepoints(self):
        flacfile = file(self.filename,"rb")

        if (flacfile.read(4) != 'fLaC'):
            flacfile.close()
            raise ValueError("not a FLAC file")

        while (True):
            (stop,header_type,length) = \
                FlacAudio.__read_flac_header__(flacfile)

            if (header_type == 5):
                cuesheet = FlacAudio.CUESHEET.parse(flacfile.read(length))

                #print repr(cuesheet)

                tracklist = cuesheet.cuesheet_tracks

                #print tracklist

                for (cur_t,next_t) in zip(tracklist,tracklist[1:]):
                    if (cur_t.track_type == 0):
                        if (next_t.track_number != 170):
                            yield (int(cur_t.track_number) - 1,
                                   "%s.1-%s.1" %
                                   (cur_t.track_number,
                                    next_t.track_number))
                        else:
                            yield (int(cur_t.track_number) - 1,
                                   "%s.1-" % (cur_t.track_number))
                flacfile.close()
                return
            else:
                flacfile.seek(length,1)

            if (stop != 0): break

        flacfile.close()
        raise ValueError("no cuesheet found")

    #generates a PCMReader object per cue point returned from cuepoints()
    def sub_pcm_tracks(self):
        for (track,points) in self.cuepoints():
            sub = subprocess.Popen([BIN['flac'],"-s","-d","-c",
                                    "--force-raw-format",
                                    "--endian=little",
                                    "--sign=signed",
                                    "--cue=%s" % (points),
                                    self.filename],
                                   stdout=subprocess.PIPE)

            yield PCMReader(sub.stdout,
                            sample_rate=self.__samplerate__,
                            channels=self.__channels__,
                            bits_per_sample=self.__bitspersample__,
                            process=sub)


#######################
#Ogg FLAC
#######################

class OggFlacAudio(FlacAudio):
    SUFFIX = "oga"
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str,range(0,9)))
    BINARIES = ("flac",)

    OGGFLAC_STREAMINFO = Con.Struct('oggflac_streaminfo',
                                    Con.Const(Con.Byte('packet_byte'),
                                              0x7F),
                                    Con.Const(Con.String('signature',4),
                                              'FLAC'),
                                    Con.Byte('major_version'),
                                    Con.Byte('minor_version'),
                                    Con.UBInt16('header_packets'),
                                    Con.Const(Con.String('flac_signature',4),
                                              'fLaC'),
                                    Con.Embed(
        FlacAudio.METADATA_BLOCK_HEADER),
                                    Con.Embed(
        FlacAudio.STREAMINFO))
    
    @classmethod
    def is_type(cls, file):
        header = file.read(0x23)

        return (header.startswith('OggS') and
                header[0x1C:0x21] == '\x7FFLAC')

    def get_metadata(self):
        stream = OggStreamReader(file(self.filename,"rb"))
        try:
            packets = stream.packets()
            
            blocks = [FlacMetaDataBlock(
                type=0,
                data=FlacAudio.STREAMINFO.build(
                  self.OGGFLAC_STREAMINFO.parse(packets.next())))]

            while (True):
                block = packets.next()
                header = FlacAudio.METADATA_BLOCK_HEADER.parse(
                    block[0:FlacAudio.METADATA_BLOCK_HEADER.sizeof()])
                blocks.append(
                    FlacMetaDataBlock(
                      type=header.block_type,
                      data=block[FlacAudio.METADATA_BLOCK_HEADER.sizeof():]))
                if (header.last_block == 1):
                    break
                
            return FlacMetaData(blocks)
        finally:
            stream.close()

    def set_metadata(self, metadata):
        import tempfile
        
        comment = FlacMetaData.converted(metadata)
        
        if (comment == None): return
        old_metadata = self.get_metadata()
        old_streaminfo = old_metadata.streaminfo
        old_seektable = old_metadata.seektable
        comment.streaminfo = old_streaminfo
        if (old_seektable is not None):
            comment.seektable = old_seektable

        reader = OggStreamReader(file(self.filename,'rb'))
        new_file = tempfile.TemporaryFile()
        writer = OggStreamWriter(new_file)

        #grab the serial number from the old file's current header
        pages = reader.pages()
        (header_page,header_data) = pages.next()
        serial_number = header_page.bitstream_serial_number
        del(pages)

        #skip the metadata packets in the old file
        packets = reader.packets(from_beginning=False)
        while (True):
            block = packets.next()
            header = FlacAudio.METADATA_BLOCK_HEADER.parse(
                block[0:FlacAudio.METADATA_BLOCK_HEADER.sizeof()])
            if (header.last_block == 1):
                break

        del(packets)

        #write our new comment blocks to the new file
        blocks = list(comment.metadata_blocks())

        #oggflac_streaminfo is a Container for STREAMINFO data
        #Ogg FLAC STREAMINFO differs from FLAC STREAMINFO,
        #so some fields need to be filled-in
        oggflac_streaminfo = FlacAudio.STREAMINFO.parse(blocks.pop(0).data)
        oggflac_streaminfo.packet_byte = 0x7F
        oggflac_streaminfo.signature = 'FLAC'
        oggflac_streaminfo.major_version = 0x1
        oggflac_streaminfo.minor_version = 0x0
        oggflac_streaminfo.header_packets = len(blocks) + 1 #+1 for padding
        oggflac_streaminfo.flac_signature = 'fLaC'
        oggflac_streaminfo.last_block = 0
        oggflac_streaminfo.block_type = 0
        oggflac_streaminfo.block_length = FlacAudio.STREAMINFO.sizeof()

        sequence_number = 0
        for (page_header,page_data) in OggStreamWriter.build_pages(
            0,serial_number,sequence_number,
            OggFlacAudio.OGGFLAC_STREAMINFO.build(oggflac_streaminfo),
            header_type=0x2):
            writer.write_page(page_header,page_data)
            sequence_number += 1

        #the non-STREAMINFO blocks are the same as FLAC, so write them out
        for block in blocks:
            for (page_header,page_data) in OggStreamWriter.build_pages(
                0,serial_number,sequence_number,
                block.build_block()):
                writer.write_page(page_header,page_data)
                sequence_number += 1

        #finally, write out a padding block
        for (page_header,page_data) in OggStreamWriter.build_pages(
            0,serial_number,sequence_number,
            FlacMetaDataBlock(type=1,
                              data=chr(0) * 4096).build_block(last=1)):
            writer.write_page(page_header,page_data)
            sequence_number += 1

            
        #now write the rest of the old pages to the new file,
        #re-sequenced and re-checksummed
        for (page,data) in reader.pages(from_beginning=False):
            page.page_sequence_number = sequence_number
            page.checksum = OggStreamReader.calculate_ogg_checksum(page,data)
            writer.write_page(page,data)
            sequence_number += 1

        reader.close()

        #re-write the file with our new data in "new_file"
        f = file(self.filename,"wb")
        new_file.seek(0,0)
        transfer_data(new_file.read,f.write)
        new_file.close()
        f.close()
        writer.close()
        

    def __read_streaminfo__(self):
        stream = OggStreamReader(file(self.filename,"rb"))
        try:
            packets = stream.packets()
            try:
                header = self.OGGFLAC_STREAMINFO.parse(packets.next())
            except Con.ConstError:
                raise FlacException('invalid Ogg FLAC streaminfo')

            self.__samplerate__ = header.samplerate
            self.__channels__ = header.channels + 1
            self.__bitspersample__ = header.bits_per_sample + 1
            self.__total_samples__ = header.total_samples
            self.__header_packets__ = header.header_packets

            self.__md5__ = "".join([chr(c) for c in header.md5])
            
            del(packets)
        finally:
            stream.close()

    def to_pcm(self):
        sub = subprocess.Popen([BIN['flac'],"-s","--ogg","-d","-c",
                                "--force-raw-format",
                                "--endian=little",
                                "--sign=signed",
                                self.filename],
                               stdout=subprocess.PIPE)
        return PCMReader(sub.stdout,
                         sample_rate=self.__samplerate__,
                         channels=self.__channels__,
                         bits_per_sample=self.__bitspersample__,
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="8"):
        SUBSTREAM_SAMPLE_RATES = frozenset([
                8000, 16000,22050,24000,32000,
                44100,48000,96000])
        SUBSTREAM_BITS = frozenset([8,12,16,20,24])

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if ((pcmreader.sample_rate in SUBSTREAM_SAMPLE_RATES) and
            (pcmreader.bits_per_sample in SUBSTREAM_BITS)):
            lax = []
        else:
            lax = ["--lax"]

        sub = subprocess.Popen([BIN['flac']] + lax + \
                               ["-s","-f","-%s" % (compression),
                                "-V","--ogg",
                                "--endian=little",
                                "--channels=%d" % (pcmreader.channels),
                                "--bps=%d" % (pcmreader.bits_per_sample),
                                "--sample-rate=%d" % (pcmreader.sample_rate),
                                "--sign=signed",
                                "--force-raw-format",
                                "-o",filename,"-"],
                               stdin=subprocess.PIPE)

        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()
        sub.wait()

        return OggFlacAudio(filename)

    def to_wave(self, wave_filename):
        if (self.__has_foreign_metadata__() and
            ('--keep-foreign-metadata' in FlacAudio.__help_output__())):
            foreign_metadata = ['--keep-foreign-metadata']
        else:
            foreign_metadata = []

        sub = subprocess.Popen([BIN['flac'],"-s","-f"] + \
                               foreign_metadata + \
                               ["-d","--ogg",
                                "-o",wave_filename,
                                self.filename])
        sub.wait()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (('--keep-foreign-metadata' in FlacAudio.__help_output__()) and
            (frozenset(WaveAudio(wave_filename).chunk_ids()) != \
             frozenset(['fmt ','data']))):
            foreign_metadata = ['--keep-foreign-metadata']
        else:
            foreign_metadata = []

        sub = subprocess.Popen([BIN['flac']] + \
                               ["-s","-f","--ogg","-%s" % (compression),
                                "-V","--lax"] + \
                               foreign_metadata + \
                               ["-o",filename,wave_filename])
        sub.wait()
        return OggFlacAudio(filename)

        
    @classmethod
    def add_replay_gain(cls, filenames):
        pass

    def cuepoints(self):
        raise ValueError("no cuesheet found")

    def sub_pcm_tracks(self):
        for i in ():
            yield i
