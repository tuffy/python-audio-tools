#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2008  Brian Langenberger

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


from audiotools import AudioFile,WaveAudio,InvalidFile,PCMReader,Con,transfer_data,subprocess,BIN,MetaData,os,re,TempWaveReader

#######################
#MONKEY'S AUDIO
#######################

class ApeTag(MetaData,dict):
    APEv2_FLAGS = Con.BitStruct("APEv2_FLAGS",
      Con.Bits("undefined1",5),
      Con.Flag("read_only"),
      Con.Bits("encoding",2),
      Con.Bits("undefined2",16),
      Con.Flag("contains_header"),
      Con.Flag("contains_no_footer"),
      Con.Flag("is_header"),
      Con.Bits("undefined3",5))

    APEv2_FOOTER = Con.Struct("APEv2",
      Con.String("preamble",8),
      Con.ULInt32("version_number"),
      Con.ULInt32("tag_size"),
      Con.ULInt32("item_count"),
      Con.Embed(APEv2_FLAGS),
      Con.ULInt64("reserved"))

    APEv2_TAG = Con.Struct("APEv2_TAG",
      Con.ULInt32("length"),
      Con.Embed(APEv2_FLAGS),
      Con.CString("key"),
      Con.MetaField("value",
        lambda ctx: ctx["length"]))

    ATTRIBUTE_MAP = {'track_name':'Title',
                     'track_number':'Track',
                     'album_name':'Album',
                     'artist_name':'Artist',
                     #"Performer" is not a defined APEv2 key
                     #it would be nice to have, yet would not be standard
                     'performer_name':'Performer',
                     'composer_name':'Composer',
                     'conductor_name':'Conductor',
                     'media':'Media',
                     'ISRC':'ISRC',
                     'catalog':'Catalog',
                     'copyright':'Copyright',
                     'publisher':'Publisher',
                     'year':'Year',
                     'date':'Record Date'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    def __init__(self, tag_dict, tag_length=None):
        try:
            track_number = int(re.findall(r'\d+',tag_dict.get('Track',u'0'))[0])
        except IndexError:
            track_number = 0

        MetaData.__init__(self,
                          track_name=tag_dict.get('Title',u''),
                          track_number=track_number,
                          album_name=tag_dict.get('Album',u''),
                          artist_name=tag_dict.get('Artist',u''),
                          performer_name=tag_dict.get('Performer',u''),
                          composer_name=tag_dict.get('Composer',u''),
                          conductor_name=tag_dict.get('Conductor',u''),
                          media=tag_dict.get('Media',u''),
                          ISRC=tag_dict.get('ISRC',u''),
                          catalog=tag_dict.get('Catalog',u''),
                          copyright=tag_dict.get('Copyright',u''),
                          publisher=tag_dict.get('Publisher',u''),
                          year=tag_dict.get('Year',u''),
                          date=tag_dict.get('Record Date',u'')
                          )
        dict.__init__(self, tag_dict)
        self.tag_length = tag_length

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (key in self.ATTRIBUTE_MAP):
            if (key not in ('track_number','album_number')):
                self[self.ATTRIBUTE_MAP[key]] = value
            else:
                self[self.ATTRIBUTE_MAP[key]] = unicode(value)

    #if a dict pair is updated (e.g. self['Title'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)

        if (self.ITEM_MAP.has_key(key)):
            if (key != 'Track'):
                self.__dict__[self.ITEM_MAP[key]] = value
            else:
                self.__dict__[self.ITEM_MAP[key]] = int(value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ApeTag))):
            return metadata
        else:
            tags = {}
            for (key,field) in cls.ITEM_MAP.items():
                if ((field == 'track_number') and
                    (getattr(metadata,field) == 0)):
                    continue

                field = unicode(getattr(metadata,field))
                if (field != u''):
                    tags[key] = field

            return ApeTag(tags)

    def __comment_name__(self):
        return u'APEv2'

    @classmethod
    def supports_images(cls):
        return False

    #takes two (key,value) apetag pairs
    #returns cmp on the weighted set of them
    #(title first, then artist, album, tracknumber)
    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {"Title":1,
                   "Album":2,
                   "Track":3,
                   "Artist":5,
                   "Performer":6,
                   "Composer":7,
                   "Conductor":8,
                   "Catalog":9,
                   "Publisher":10,
                   "ISRC":11,
                   "Media":12,
                   "Year":13,
                   "Record Date":14,
                   "Copyright":15}

        return cmp((KEY_MAP.get(pair1[0],16),pair1[0],pair1[1]),
                   (KEY_MAP.get(pair2[0],16),pair2[0],pair2[1]))

    def __comment_pairs__(self):
        items = []

        for (key,value) in self.items():
            if (isinstance(value,unicode)):
                items.append((key,value))
            else:
                if (len(value) <= 20):
                    items.append((key,value.encode('hex')))
                else:
                    items.append((key,value.encode('hex')[0:39].upper() + u"\u2026"))

        return sorted(items,ApeTag.__by_pair__)


    #Takes a file object of a Monkey's Audio file
    #and returns a tuple.
    #That tuple contains the dict of its APE tag info
    #and the total tag size.
    @classmethod
    def read_ape_tag(cls, apefile):
        apefile.seek(-32,2)
        footer = cls.APEv2_FOOTER.parse(apefile.read(32))

        if (footer.preamble != 'APETAGEX'):
            return ({},0)

        apefile.seek(-(footer.tag_size),2)

        apev2tag = {}

        for tag in Con.StrictRepeater(footer.item_count,
                                      cls.APEv2_TAG).parse(apefile.read()):
            if (tag.encoding == 0):
                apev2tag[tag.key] = tag.value.rstrip("\0").decode('utf-8',
                                                                  'replace')
            else:
                apev2tag[tag.key] = tag.value

        if (footer.contains_header):
            return (apev2tag,
                    footer.tag_size + ApeTag.APEv2_FOOTER.sizeof())
        else:
            return (apev2tag,
                    footer.tag_size)

    def ape_tag_data(self):
        header = Con.Container()
        header.preamble = 'APETAGEX'
        header.version_number = 0x07D0
        header.tag_size = 0
        header.item_count = len(self.keys())

        header.undefined1 = header.undefined2 = header.undefined3 = 0
        header.read_only = False
        header.encoding = 0
        header.contains_header = True
        header.contains_no_footer = False
        header.is_header = True

        header.reserved = 0l

        footer = Con.Container()
        footer.preamble = header.preamble
        footer.version_number = header.version_number
        footer.tag_size = 0
        footer.item_count = len(self.keys())

        footer.undefined1 = footer.undefined2 = footer.undefined3 = 0
        footer.read_only = False
        footer.encoding = 0
        footer.contains_header = True
        footer.contains_no_footer = False
        footer.is_header = False

        footer.reserved = 0l

        tags = []
        for (key,value) in self.items():
            tag = Con.Container()

            if (isinstance(value,unicode)):
                value = value.encode('utf-8')
                tag.encoding = 0
            else:
                tag.encoding = 1

            tag.length = len(value)
            tag.key = key
            tag.value = value

            tag.undefined1 = tag.undefined2 = tag.undefined3 = 0
            tag.read_only = False
            tag.contains_header = False
            tag.contains_no_footer = False
            tag.is_header = False

            tags.append(ApeTag.APEv2_TAG.build(tag))
        tags = "".join(tags)

        footer.tag_size = header.tag_size = \
          len(tags) + len(ApeTag.APEv2_FOOTER.build(footer))

        return ApeTag.APEv2_FOOTER.build(header) + \
               tags + \
               ApeTag.APEv2_FOOTER.build(footer)

#This is a split-off version of get_metadata() and set_metadata()
#for formats with an appended APEv2 tag.
#This class presumes there will be a filename attribute which
#can be opened and checked for tags, or written if necessary.
class ApeTaggedAudio:
    def get_metadata(self):
        f = file(self.filename,'rb')
        try:
            (info,tag_length) = ApeTag.read_ape_tag(f)
            if (len(info) > 0):
                return ApeTag(info,tag_length)
            else:
                return None
        finally:
            f.close()

    def set_metadata(self, metadata):
        apetag = ApeTag.converted(metadata)

        if (apetag is None): return

        current_metadata = self.get_metadata()
        if (current_metadata != None):  #there's existing tags to delete
            f = file(self.filename,"rb")
            untagged_data = f.read()[0:-current_metadata.tag_length]
            f.close()
            f = file(self.filename,"wb")
            f.write(untagged_data)
            f.write(apetag.ape_tag_data())
            f.close()
        else:                           #no existing tags
            f = file(self.filename,"ab")
            f.write(apetag.ape_tag_data())
            f.close()


class ApeAudio(ApeTaggedAudio,AudioFile):
    SUFFIX = "ape"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "5000"
    COMPRESSION_MODES = tuple([str(x * 1000) for x in range(1,6)]); del(x)
    BINARIES = ("mac",)

    FILE_HEAD = Con.Struct("ape_head",
                           Con.String('id',4),
                           Con.ULInt16('version'))

    #version >= 3.98
    APE_DESCRIPTOR = Con.Struct("ape_descriptor",
                                Con.ULInt16('padding'),
                                Con.ULInt32('descriptor_bytes'),
                                Con.ULInt32('header_bytes'),
                                Con.ULInt32('seektable_bytes'),
                                Con.ULInt32('header_data_bytes'),
                                Con.ULInt32('frame_data_bytes'),
                                Con.ULInt32('frame_data_bytes_high'),
                                Con.ULInt32('terminating_data_bytes'),
                                Con.String('md5',16))

    APE_HEADER = Con.Struct("ape_header",
                            Con.ULInt16('compression_level'),
                            Con.ULInt16('format_flags'),
                            Con.ULInt32('blocks_per_frame'),
                            Con.ULInt32('final_frame_blocks'),
                            Con.ULInt32('total_frames'),
                            Con.ULInt16('bits_per_sample'),
                            Con.ULInt16('number_of_channels'),
                            Con.ULInt32('sample_rate'))

    #version <= 3.97
    APE_HEADER_OLD = Con.Struct("ape_header_old",
                                Con.ULInt16('compression_level'),
                                Con.ULInt16('format_flags'),
                                Con.ULInt16('number_of_channels'),
                                Con.ULInt32('sample_rate'),
                                Con.ULInt32('header_bytes'),
                                Con.ULInt32('terminating_bytes'),
                                Con.ULInt32('total_frames'),
                                Con.ULInt32('final_frame_blocks'))

    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        (self.__samplespersec__,
         self.__channels__,
         self.__bitspersample__,
         self.__totalsamples__) = ApeAudio.__ape_info__(filename)

    @classmethod
    def is_type(cls, file):
        return file.read(4) == "MAC "

    def lossless(self):
        return True

    @classmethod
    def supports_foreign_riff_chunks(cls):
        return True

    def bits_per_sample(self):
        return self.__bitspersample__

    def channels(self):
        return self.__channels__

    def total_frames(self):
        return self.__totalsamples__

    def sample_rate(self):
        return self.__samplespersec__


    @classmethod
    def __ape_info__(cls, filename):
        f = file(filename,'rb')
        try:
            file_head = cls.FILE_HEAD.parse_stream(f)

            if (file_head.id != 'MAC '):
                raise InvalidFile("invalid Monkey's Audio header")

            if (file_head.version >= 3980): #the latest APE file type
                descriptor = cls.APE_DESCRIPTOR.parse_stream(f)
                header = cls.APE_HEADER.parse_stream(f)

                return (header.sample_rate,
                        header.number_of_channels,
                        header.bits_per_sample,
                        ((header.total_frames - 1) * \
                         header.blocks_per_frame) + \
                         header.final_frame_blocks)
            else:                           #old-style APE file (obsolete)
                header = cls.APE_HEADER_OLD.parse_stream(f)

                if (file_head.version >= 3950):
                    blocks_per_frame = 0x48000
                elif ((file_head.version >= 3900) or
                      ((file_head.version >= 3800) and
                       (header.compression_level == 4000))):
                    blocks_per_frame = 0x12000
                else:
                    blocks_per_frame = 0x2400

                if (header.format_flags & 0x01):
                    bits_per_sample = 8
                elif (header.format_flags & 0x08):
                    bits_per_sample = 24
                else:
                    bits_per_sample = 16

                return (header.sample_rate,
                        header.number_of_channels,
                        bits_per_sample,
                        ((header.total_frames - 1) * \
                         blocks_per_frame) + \
                         header.final_frame_blocks)

        finally:
            f.close()

    def to_pcm(self):
        import tempfile

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        self.to_wave(f.name)
        f.seek(0,0)
        return TempWaveReader(f)

    def to_wave(self, wave_filename):
        if (self.filename.endswith(".ape")):
            devnull = file(os.devnull,"wb")
            sub = subprocess.Popen([BIN['mac'],
                                    self.filename,
                                    wave_filename,
                                    '-d'],
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()
        else:
            devnull = file(os.devnull,'ab')
            import tempfile
            ape = tempfile.NamedTemporaryFile(suffix='.ape')
            f = file(self.filename,'rb')
            transfer_data(f.read,ape.write)
            f.close()
            ape.flush()
            sub = subprocess.Popen([BIN['mac'],
                                    ape.name,
                                    wave_filename,
                                    '-d'],
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            ape.close()
            devnull.close()


    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import tempfile

        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        w = WaveAudio.from_pcm(f.name, pcmreader)
        try:
            return cls.from_wave(filename,f.name,compression)
        finally:
            del(w)
            f.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        devnull = file(os.devnull,"wb")
        sub = subprocess.Popen([BIN['mac'],
                                wave_filename,
                                filename,
                                "-c%s" % (compression)],
                               stdout=devnull,
                               stderr=devnull)
        sub.wait()
        devnull.close()
        return ApeAudio(filename)
