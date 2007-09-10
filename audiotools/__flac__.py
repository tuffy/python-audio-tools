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


from audiotools import AudioFile,InvalidFile,PCMReader,Con,transfer_data,subprocess,BIN,cStringIO,open_files,Image,ImageMetaData
from __vorbiscomment__ import *
from __id3__ import ID3v2Comment
from __vorbis__ import OggStreamReader,OggStreamWriter


#######################
#FLAC
#######################

class FlacException(InvalidFile): pass

#this is a container for FLAC's PICTURE metadata blocks
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
                       description=description.decode('utf-8'),
                       type={3:0,4:1,5:2,6:3}.get(type,4))
        self.flac_type = type

    #takes an Image object
    #returns a FlacPictureComment
    @classmethod
    def converted(cls, image):
        return FlacPictureComment(type={0:3,1:4,5:2,3:6}.get(image.type,0),
                                  mime_type=image.mime_type,
                                  description=image.description.encode('utf-8'),
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
        return "FlacPictureComment(type=%s,mime_type=%s,width=%s,height=%s,...)" % \
               (repr(self.flac_type),repr(self.mime_type),
                repr(self.width),repr(self.height))

    def __unicode__(self):
        return u"Picture : %s (%d\u00D7%d,'%s')" % \
            (self.type_string(),
             self.width,self.height,self.mime_type)

    def build(self):
        return FlacAudio.PICTURE_COMMENT.build(
            Con.Container(type=self.flac_type,
                          mime_type=self.mime_type,
                          description=self.description,
                          width=self.width,
                          height=self.height,
                          color_depth=self.color_depth,
                          color_count=self.color_count,
                          data=self.data))

#FIXME - implement add_image,delete_image
class FlacComment(ImageMetaData,VorbisComment):
    VORBIS_COMMENT = Con.Struct("vorbis_comment",
                                Con.PascalString("vendor_string",
                                                 length_field=Con.ULInt32("length")),
                                Con.PrefixedArray(
        length_field=Con.ULInt32("length"),
        subcon=Con.PascalString("value",
                                length_field=Con.ULInt32("length"))))

    #picture_comments should be a list of FlacPictureComments
    def __init__(self, vorbis_comment, picture_comments=()):
        #self.picture_comments = picture_comments
        VorbisComment.__init__(self,vorbis_comment)
        ImageMetaData.__init__(self,picture_comments)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,FlacComment))):
            return metadata
        else:
            if (isinstance(metadata,ImageMetaData)):
                images = [FlacPictureComment.converted(i)
                          for i in metadata.images()]
                
            if (isinstance(metadata,VorbisComment)):
                return FlacComment(metadata,images)
            else:
                return FlacComment(VorbisComment.converted(metadata),images)

    def __unicode__(self):
        if (len(self.images()) == 0):
            return unicode(VorbisComment.__unicode__(self))
        else:
            return u"%s\n\n%s" % \
                (unicode(VorbisComment.__unicode__(self)),
                 "\n".join([unicode(p) for p in self.images()]))


class FlacAudio(AudioFile):
    SUFFIX = "flac"
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str,range(0,9)))
    BINARIES = ("flac","metaflac")
    
    
    FLAC_METADATA_BLOCK_HEADER = Con.BitStruct("metadata_block_header",
                                            Con.Bit("last_block"),
                                            Con.Bits("block_type",7),
                                            Con.Bits("block_length",24))
    
    FLAC_STREAMINFO = Con.Struct("flac_streaminfo",
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

    #returns a MetaData-compatible VorbisComment for this FLAC files
    def get_metadata(self):
        f = file(self.filename,"rb")
        try:
            vorbiscomment = VorbisComment({})
            image_blocks = []

            if (f.read(4) != 'fLaC'):
                return vorbiscomment
            
            stop = 0
            while (stop == 0):
                (stop,header_type,length) = FlacAudio.__read_flac_header__(f)
                if (header_type == 4):
                    vorbiscomment = VorbisComment(
                        FlacAudio.__read_vorbis_comment__(
                            cStringIO.StringIO(f.read(length))))
                elif (header_type == 6):
                    image = FlacAudio.PICTURE_COMMENT.parse(
                        f.read(length))
                    image_blocks.append(FlacPictureComment(
                        type=image.type,
                        mime_type=image.mime_type,
                        description=image.description,
                        width=image.width,
                        height=image.height,
                        color_depth=image.color_depth,
                        color_count=image.color_count,
                        data=image.data))
                else:
                    f.seek(length,1)

            return FlacComment(vorbiscomment,tuple(image_blocks))
        finally:
            f.close()

    def set_metadata(self, metadata):
        metadata = FlacComment.converted(metadata)
        
        if (metadata == None): return

        subprocess.call([BIN['metaflac'],'--remove-all-tags',self.filename])

        import tempfile
        
        self.__set_vorbis_comment__(metadata)

        #converted() must transform all ImageMetaData to FlacPictureComments
        for picture in metadata.images():
            picturedata = tempfile.NamedTemporaryFile()
            picturedata.write(picture.data)
            picturedata.flush()
            self.set_picture(picture_filename=picturedata.name,
                             type=picture.flac_type,
                             mime_type=picture.mime_type,
                             description=picture.description,
                             width=picture.width,
                             height=picture.height,
                             depth=picture.color_depth,
                             colors=picture.color_count)
            picturedata.close()



    def __set_vorbis_comment__(self, metadata):
        #sets VorbisComment metadata for this file,
        #but without clearing all the tags first
        tags = []
        for (key,values) in metadata.items():
            for value in values:
                tags.append((key,value))
        subprocess.call([BIN['metaflac']] + \
                            ["--set-tag=%s=%s" % (key,value)
                             for (key,value) in tags] + \
                            [self.filename])

    def set_picture(self, picture_filename, type=3,
                    mime_type="",description="",
                    width=None,height=None,depth=None,colors=None):
        if ((width != None) and (height != None) and
            (depth != None) and (colors != None)):
            colorspec = "%dx%dx%d/%d" % \
                (width,height,depth,colors)
        else:
            colorspec = ""

        subprocess.call([BIN['metaflac']] + \
                        ["--import-picture-from=%s" % \
                          ("|".join((str(type),mime_type,
                                     description,colorspec,
                                     picture_filename)))] + \
                        [self.filename])

    @classmethod
    def __read_flac_header__(cls, flacfile):
        p = FlacAudio.FLAC_METADATA_BLOCK_HEADER.parse(flacfile.read(4))
        return (p.last_block, p.block_type, p.block_length)

    #takes the vorbis comment block of a flacfile file handle
    #and returns a key->comment_list hashtable
    @classmethod
    def __read_vorbis_comment__(cls, flacfile):
        comment_table = {}

        flacdata = flacfile.read()

        for comment in FlacComment.VORBIS_COMMENT.parse(flacdata).value:
            key = comment[0:comment.index("=")].upper()
            comment = comment[comment.index("=") + 1:].decode('utf-8')
            
            comment_table.setdefault(key,[]).append(comment)


        return comment_table
    
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
        pcmreader.close()
        sub.stdin.close()
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
    
        p = FlacAudio.FLAC_STREAMINFO.parse(f.read(length))

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
        
        if (len(track_names) > 0):
            subprocess.call([BIN['metaflac'],'--add-replay-gain'] + \
                            track_names)

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
    
    #def __read_flac_header__(self, flacfile):
    #    p = FlacAudio.FLAC_METADATA_BLOCK_HEADER.parse(flacfile.read(4))
    #    return (p.last_block, p.block_type, p.block_length)

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
        FlacAudio.FLAC_METADATA_BLOCK_HEADER),
                                    Con.Embed(
        FlacAudio.FLAC_STREAMINFO))
    
    @classmethod
    def is_type(cls, file):
        header = file.read(0x23)

        return (header.startswith('OggS') and
                header[0x1C:0x21] == '\x7FFLAC')

    def get_metadata(self):
        stream = OggStreamReader(file(self.filename,"rb"))
        try:
            packets = stream.packets()
            packets.next()           #skip the header packet
            comment = packets.next() #comment packet must be next
            pictures = []

            for p in packets:   
                header = FlacAudio.FLAC_METADATA_BLOCK_HEADER.parse(p[0:4])
                if (header.block_type == 6):
                    image = FlacAudio.PICTURE_COMMENT.parse(
                        p[4:])
                    pictures.append(FlacPictureComment(
                        type=image.type,
                        mime_type=image.mime_type,
                        description=image.description,
                        width=image.width,
                        height=image.height,
                        color_depth=image.color_depth,
                        color_count=image.color_count,
                        data=image.data))
                    
                if (header.last_block == 1):
                    break

            return FlacComment(
                FlacAudio.__read_vorbis_comment__(
                  cStringIO.StringIO(
                    comment[4:])),
                tuple(pictures))
        finally:
            stream.close()

    def set_metadata(self, metadata):
        comment = FlacComment.converted(metadata)
        
        if (comment == None): return

        reader = OggStreamReader(file(self.filename,'rb'))
        new_file = cStringIO.StringIO()
        writer = OggStreamWriter(new_file)

        pages = reader.pages()

        #transfer our old header
        (header_page,header_data) = pages.next()
        writer.write_page(header_page,header_data)

        #skip the old VORBIS_COMMENT packet (required to be next in the stream)
        (page,data) = pages.next()
        while (page.segment_lengths[-1] == 255):
            (page,data) = pages.next()
        

        #write the pages for our new comment packet
        comment_pages = OggStreamWriter.build_pages(
            0,
            header_page.bitstream_serial_number,
            header_page.page_sequence_number + 1,
            FlacAudio.FLAC_METADATA_BLOCK_HEADER.build(
              Con.Container(last_block=0,
                            block_type=4,
                            block_length=len(comment.build()))) + \
            comment.build())

        for (page,data) in comment_pages:
            writer.write_page(page,data)

        #write the pages for PICTURE comment packets (if any)
        pagenum = comment_pages[-1][0].page_sequence_number + 1

        for picture in comment.picture_comments:
            picture_pages = OggStreamWriter.build_pages(
                0,
                header_page.bitstream_serial_number,
                header_page.page_sequence_number + pagenum,
                FlacAudio.FLAC_METADATA_BLOCK_HEADER.build(
                  Con.Container(last_block=0,
                                block_type=6,
                                block_length=len(picture.build()))) + \
                picture.build())
            
            for (page,data) in picture_pages:
                writer.write_page(page,data)
                pagenum += 1

        #skip any old PICTURE comment packets (if any)
        #until the end of the metadata blocks
        metadata_packet = OggStreamReader.pages_to_packet(pages)
        header = FlacAudio.FLAC_METADATA_BLOCK_HEADER.parse(
            metadata_packet[0][1][0:4])
        
        while (header.last_block == 0):
            if (header.block_type != 6):
                for (page,data) in metadata_packet:
                    page.page_sequence_number = pagenum
                    page.checksum = \
                         OggStreamReader.calculate_ogg_checksum(page,data)
                    writer.write_page(page,data)
                    pagenum += 1
                    
            metadata_packet = OggStreamReader.pages_to_packet(pages)
            header = FlacAudio.FLAC_METADATA_BLOCK_HEADER.parse(
                metadata_packet[0][1][0:4])

        #write out that last metadata block (hopefully not a picture)
        for (page,data) in metadata_packet:
            page.page_sequence_number = pagenum
            page.checksum = OggStreamReader.calculate_ogg_checksum(page,data)
            writer.write_page(page,data)
            pagenum += 1
        
        #write the rest of the pages, re-sequenced and re-checksummed
        for (i,(page,data)) in enumerate(pages):
            page.page_sequence_number = pagenum + i
            page.checksum = OggStreamReader.calculate_ogg_checksum(page,data)
            writer.write_page(page,data)

        reader.close()

        #re-write the file with our new data in "new_file"
        f = file(self.filename,"wb")
        f.write(new_file.getvalue())
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

            #FIXME
            #(might not be valid for PCM-generated OggFLAC
            # we should probably bounce to the end of the file)
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

        
    @classmethod
    def add_replay_gain(cls, filenames):
        pass

    def cuepoints(self):
        raise ValueError("no cuesheet found")

    def sub_pcm_tracks(self):
        for i in ():
            yield i
