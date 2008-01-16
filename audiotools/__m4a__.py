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


from audiotools import AudioFile,InvalidFile,PCMReader,PCMConverter,Con,transfer_data,subprocess,BIN,cStringIO,MetaData,os,Image,ignore_sigint

#######################
#M4A File
#######################

#M4A files are made up of QuickTime Atoms
#some of those Atoms are containers for sub-Atoms
class __Qt_Atom__:
    CONTAINERS = frozenset(
        ['dinf', 'edts', 'imag', 'imap', 'mdia', 'mdra', 'minf', 
         'moov', 'rmra', 'stbl', 'trak', 'tref', 'udta', 'vnrp'])

    STRUCT = Con.Struct("qt_atom",
                     Con.UBInt32("size"),
                     Con.String("type",4))

    def __init__(self, type, data):
        self.type = type
        self.data = data

    #takes an 8 byte string
    #returns an Atom's (type,size) as a tuple
    @classmethod
    def parse(cls, header_data):
        header = cls.STRUCT.parse(header_data)
        return (header.type,header.size)

    #performs a search of all sub-atoms to find the one
    #with the given type, or None if one cannot be found
    def get_atom(self, type):
        if (self.type == type):
            return self
        elif (self.is_container()):
            for atom in self:
                returned_atom = atom.get_atom(type)
                if (returned_atom != None):
                    return returned_atom

        return None

    #returns True if the Atom is a container, False if not
    def is_container(self):
        return self.type in self.CONTAINERS

    def __iter__(self):
        for atom in __parse_qt_atoms__(cStringIO.StringIO(self.data),
                                       __Qt_Atom__):
            yield atom

    def __len__(self):
        count = 0
        for atom in self:
            count += 1
        return count

    def __getitem__(self, type):
        for atom in self:
            if (atom.type == type):
                return atom
        raise KeyError(type)

    def keys(self):
        return [atom.type for atom in self]


class __Qt_Meta_Atom__(__Qt_Atom__):
    CONTAINERS = frozenset(
        ['aaid','\xa9alb','akid','apid','\xa9ART','\xa9cmt',
         '\xa9com','covr','cpil','cptr','\xa9day','disk',
         'geid','gnre','\xa9grp','\xa9nam','plid','rtnd',
         'stik','tmpo','\xa9too','trkn','\xa9wrt','----',
         'meta'])

    TRKN = Con.Struct('trkn',
                      Con.Padding(2),
                      Con.UBInt16('track_number'),
                      Con.UBInt16('total_tracks'),
                      Con.Padding(2))

    def __init__(self, type, data):
        self.type = type

        if (type == 'meta'):
            self.data = data[4:]
        else:
            self.data = data

    def __iter__(self):
        for atom in __parse_qt_atoms__(cStringIO.StringIO(self.data),
                                       __Qt_Meta_Atom__):
            yield atom


#a stream of __Qt_Atom__ objects
#though it is an Atom-like container, it has no type of its own
class __Qt_Atom_Stream__(__Qt_Atom__):
    def __init__(self, stream):
        self.stream = stream
        self.atom_class = __Qt_Atom__
        
        __Qt_Atom__.__init__(self,None,None)

    def is_container(self):
        return True

    def __iter__(self):
        self.stream.seek(0,0)

        for atom in __parse_qt_atoms__(self.stream,
                                       self.atom_class):
            yield atom

#takes a stream object with a read() method
#iterates over all of the atoms it contains and yields
#a series of qt_class objects, which defaults to __Qt_Atom__
def __parse_qt_atoms__(stream, qt_class=__Qt_Atom__):
    h = stream.read(8)
    while (len(h) == 8):
        (header_type,header_size) = qt_class.parse(h)
        if (header_size == 0):
            yield qt_class(header_type,stream.read())
        else:
            yield qt_class(header_type,stream.read(header_size - 8))

        h = stream.read(8)

def __build_qt_atom__(atom_type, atom_data):
    con = Con.Container()
    con.type = atom_type
    con.size = len(atom_data) + __Qt_Atom__.STRUCT.sizeof()
    return __Qt_Atom__.STRUCT.build(con) + atom_data
    

#takes an existing __Qt_Atom__ object (possibly a container)
#and a __Qt_Atom__ to replace
#finds all sub-atoms with the same type as new_atom and replaces them
#returns a string
def __replace_qt_atom__(qt_atom, new_atom):
    if (qt_atom.type == None):
        return "".join(
            [__replace_qt_atom__(a, new_atom) for a in qt_atom])
    elif (qt_atom.type == new_atom.type):
        #if we've found the atom to replace,
        #build a new atom string from new_atom's data
        return __build_qt_atom__(new_atom.type,new_atom.data)
    else:
        #if we're still looking for the atom to replace
        if (not qt_atom.is_container()):
            #build the old atom string from qt_atom's data
            #if it is not a container
            return __build_qt_atom__(qt_atom.type,qt_atom.data)
        else:
            #recursively build the old atom's data
            #with values from __replace_qt_atom__
            return __build_qt_atom__(qt_atom.type,
                                     "".join(
                    [__replace_qt_atom__(a,new_atom) for a in qt_atom]))


class M4AAudio(AudioFile):
    SUFFIX = "m4a"
    DEFAULT_COMPRESSION = "100"
    COMPRESSION_MODES = tuple(["10"] + map(str,range(50,500,25)) + ["500"])
    BINARIES = ("faac","faad")

    MP4A_ATOM = Con.Struct("mp4a",
                           Con.UBInt32("length"),
                           Con.String("type",4),
                           Con.String("reserved",6),
                           Con.UBInt16("reference_index"),
                           Con.UBInt16("version"),
                           Con.UBInt16("revision_level"),
                           Con.String("vendor",4),
                           Con.UBInt16("channels"),
                           Con.UBInt16("bits_per_sample"))

    MDHD_ATOM = Con.Struct("mdhd",
                           Con.Byte("version"),
                           Con.Bytes("flags",3),
                           Con.UBInt32("creation_date"),
                           Con.UBInt32("modification_date"),
                           Con.UBInt32("sample_rate"),
                           Con.UBInt32("track_length"))

    def __init__(self, filename):
        self.filename = filename
        self.qt_stream = __Qt_Atom_Stream__(file(self.filename,"rb"))

        try:
            mp4a = M4AAudio.MP4A_ATOM.parse(
                self.qt_stream['moov']['trak']['mdia']['minf']['stbl']['stsd'].data[8:])

            self.__channels__ = mp4a.channels
            self.__bits_per_sample__ = mp4a.bits_per_sample

            mdhd = M4AAudio.MDHD_ATOM.parse(
                self.qt_stream['moov']['trak']['mdia']['mdhd'].data)

            self.__sample_rate__ = mdhd.sample_rate
            self.__length__ = mdhd.track_length
        except KeyError:
            raise InvalidFile('required moov atom not found')

    @classmethod
    def is_type(cls, file):
        header = file.read(12)
        
        return ((header[4:8] == 'ftyp') and
                (header[8:12] in ('mp41','mp42','M4A ','M4B ')))

    def lossless(self):
        return False

    def channels(self):
        return self.__channels__

    def bits_per_sample(self):
        return self.__bits_per_sample__

    def sample_rate(self):
        return self.__sample_rate__

    def cd_frames(self):
        return (self.__length__ - 1024) / self.__sample_rate__ * 75

    def total_frames(self):
        return self.__length__ - 1024

    def get_metadata(self):
        meta_atom = self.qt_stream['moov']['udta']['meta']
        meta_atom = __Qt_Meta_Atom__(meta_atom.type,
                                     meta_atom.data)
        data = {}
        for atom in meta_atom['ilst']:
            if (atom.type.startswith('\xa9') or (atom.type == 'cprt')):
                data.setdefault(atom.type,
                                []).append(atom['data'].data[8:].decode('utf-8'))
            else:
                data.setdefault(atom.type,
                                []).append(atom['data'].data[8:])

        return M4AMetaData(data)

    def set_metadata(self, metadata):
        metadata = M4AMetaData.converted(metadata)
        if (metadata is None): return
        
        new_file = __replace_qt_atom__(self.qt_stream,
                                       metadata.to_atom())
        f = file(self.filename,"wb")
        f.write(new_file)
        f.close()

        f = file(self.filename,"rb")
        self.qt_stream = __Qt_Atom_Stream__(f)
        

    def to_pcm(self):
        devnull = file(os.devnull,"ab")

        sub = subprocess.Popen([BIN['faad'],"-f",str(2),"-w",
                                self.filename],
                               stdout=subprocess.PIPE,
                               stderr=devnull)
        return PCMReader(sub.stdout,
                         sample_rate=self.__sample_rate__,
                         channels=self.__channels__,
                         bits_per_sample=self.__bits_per_sample__,
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="100"):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.channels > 2):
            pcmreader = PCMConverter(pcmreader,
                                     sample_rate=pcmreader.sample_rate,
                                     channels=2,
                                     bits_per_sample=pcmreader.bits_per_sample)

        devnull = file(os.devnull,"ab")

        sub = subprocess.Popen([BIN['faac'],
                                "-q",compression,
                                "-P",
                                "-R",str(pcmreader.sample_rate),
                                "-B",str(pcmreader.bits_per_sample),
                                "-C",str(pcmreader.channels),
                                "-X",
                                "-o",filename,
                                "-"],
                               stdin=subprocess.PIPE,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)
        #Note: faac handles SIGINT on its own,
        #so trying to ignore it doesn't work like on most other encoders.
        
        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()
        sub.wait()

        return M4AAudio(filename)

class M4AMetaData(MetaData,dict):
    #meta_data is a key->[value1,value2,...] dict of the contents
    #of the 'meta' container atom
    #values are Unicode if the key starts with \xa9, binary strings otherwise
    def __init__(self, meta_data):
        trkn = __Qt_Meta_Atom__.TRKN.parse(
            meta_data.get('trkn',[chr(0) * 8])[0])

        if (meta_data.has_key('covr')):
            images = [M4ACovr(i) for i in meta_data['covr']]
        else:
            images = []

        MetaData.__init__(self,
                          track_name=meta_data.get('\xa9nam',[u''])[0],
                          track_number=trkn.track_number,
                          album_name=meta_data.get('\xa9alb',[u''])[0],
                          artist_name=meta_data.get('\xa9wrt',[u''])[0],
                          performer_name=meta_data.get('\xa9ART',[u''])[0],
                          copyright=meta_data.get('cprt',[u''])[0],
                          year=u'',
                          images=images)

        dict.__init__(self, meta_data)

    ATTRIBUTE_MAP = {'track_name':'\xa9nam',
                     'track_number':'trkn',
                     'album_name':'\xa9alb',
                     'artist_name':'\xa9wrt',
                     'performer_name':'\xa9ART',
                     'copyright':'cprt',
                     'year':'\xa9day'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value
        
        if (self.ATTRIBUTE_MAP.has_key(key)):
            if (key != 'track_number'):
                self[self.ATTRIBUTE_MAP[key]] = [value]
            else:
                trkn = [__Qt_Meta_Atom__.TRKN.build(Con.Container(
                    track_number=int(value),
                    total_tracks=0))]
                
                self[self.ATTRIBUTE_MAP[key]] = trkn

    #if a dict pair is updated (e.g. self['\xa9nam'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        
        if (self.ITEM_MAP.has_key(key)):
            if (key != 'trkn'):
                self.__dict__[self.ITEM_MAP[key]] = value[0]
            else:
                trkn = __Qt_Meta_Atom__.TRKN.parse(value[0])
                self.__dict__[self.ITEM_MAP[key]] = trkn.track_number

    def add_image(self, image):
        if (image.type == 0):
            self.setdefault('covr',[]).append(image.data)
            MetaData.add_image(self,M4ACovr.converted(image))

    def delete_image(self, image):
        del(self['covr'][self['covr'].index(image.data)])
        MetaData.delete_image(self,image)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,M4AMetaData))):
            return metadata
        
        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            value = getattr(metadata,field)
            if (field != 'track_number'):
                if (value != u''):
                    tags[key] = [value]
            else:
                tags['trkn'] = [__Qt_Meta_Atom__.TRKN.build(Con.Container(
                    track_number=int(value),
                    total_tracks=0))]

        if (len(metadata.front_covers()) > 0):
            tags['covr'] = [i.data for i in metadata.front_covers()]
        
        return M4AMetaData(tags)

    #returns the contents of this M4AMetaData as a 'meta' atom string
    def to_atom(self):
        hdlr = __build_qt_atom__(
            'hdlr',
            (chr(0) * 8) + 'mdirappl' + (chr(0) * 10))
        
        ilst = []
        for (key,values) in self.items():
            for value in values:
                if (isinstance(value,unicode)):
                    ilst.append(
                        __build_qt_atom__(
                          key,
                          __build_qt_atom__('data',
                                            '\x00\x00\x00\x01\x00\x00\x00\x00' + \
                                            value.encode('utf-8'))))
                else:
                    ilst.append(
                        __build_qt_atom__(
                          key,
                          __build_qt_atom__('data',
                                            '\x00\x00\x00\x00\x00\x00\x00\x00' + \
                                            value)))

        return __Qt_Atom__('meta',
                           (chr(0) * 4) + \
                           hdlr + \
                           __build_qt_atom__('ilst',"".join(ilst)) + \
                           __build_qt_atom__('free',chr(0) * 2040))
                           


    def __comment_name__(self):
        return u'M4A'

    @classmethod
    def supports_images(self):
        return True

    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {" nam":1,
                   " ART":5,
                   " com":4,
                   " alb":2,
                   "trkn":3,
                   "----":7}

        return cmp((KEY_MAP.get(pair1[0],6),pair1[0],pair1[1]),
                   (KEY_MAP.get(pair2[0],6),pair2[0],pair2[1]))

    def __comment_pairs__(self):
        pairs = []
        for (key,values) in self.items():
            for value in values:
                if (key.startswith('\xa9') or (key == 'cprt')):
                    pairs.append((key.replace('\xa9',' '),value))
                elif (key == 'trkn'):
                    tracknumber = __Qt_Meta_Atom__.TRKN.parse(value)
                    
                    pairs.append((key,"%s/%s" % (tracknumber.track_number,
                                                 tracknumber.total_tracks)))
                else:
                    if (len(value) <= 20):
                        pairs.append(
                            (key,
                             unicode(value.encode('hex').upper())))
                    else:
                        pairs.append(
                            (key,
                             unicode(value.encode('hex')[0:39].upper()) + \
                                 u"\u2026"))

        pairs.sort(M4AMetaData.__by_pair__)
        return pairs

class M4ACovr(Image):
    def __init__(self, image_data):
        self.image_data = image_data

        img = Image.new(image_data,u'',0)
 
        Image.__init__(self,
                       data=image_data,
                       mime_type=img.mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=img.description,
                       type=img.type)

    @classmethod
    def converted(cls, image):
        return M4ACovr(image.data)
