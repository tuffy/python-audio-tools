#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2009  Brian Langenberger

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


from audiotools import AudioFile,InvalidFile,PCMReader,PCMConverter,Con,transfer_data,subprocess,BIN,cStringIO,MetaData,os,Image,InvalidImage,ignore_sigint,InvalidFormat,open,open_files,EncodingError,DecodingError,WaveAudio,TempWaveReader,PCMReaderError
from __m4a_atoms__ import *
import gettext

gettext.install("audiotools",unicode=True)

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

    def __init__(self, type, data, offset):
        self.type = type
        self.data = data
        self.offset = offset

    def __repr__(self):
        return "__Qt_Atom__(%s,%s,%s)" % \
            (repr(self.type),
             repr(self.data),
             repr(self.offset))

    def __eq__(self, o):
        if (hasattr(o,"type") and
            hasattr(o,"data")):
            return ((self.type == o.type) and
                    (self.data == o.data))
        else:
            return False

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

#a stream of __Qt_Atom__ objects
#though it is an Atom-like container, it has no type of its own
class __Qt_Atom_Stream__(__Qt_Atom__):
    def __init__(self, stream):
        self.stream = stream
        self.atom_class = __Qt_Atom__

        __Qt_Atom__.__init__(self,None,None,0)

    def is_container(self):
        return True

    def __iter__(self):
        self.stream.seek(0,0)

        for atom in __parse_qt_atoms__(self.stream,
                                       self.atom_class,
                                       self.offset):
            yield atom

#takes a stream object with a read() method
#iterates over all of the atoms it contains and yields
#a series of qt_class objects, which defaults to __Qt_Atom__
def __parse_qt_atoms__(stream, qt_class=__Qt_Atom__, base_offset=0):
    h = stream.read(8)
    while (len(h) == 8):
        (header_type,header_size) = qt_class.parse(h)
        if (header_size == 0):
            yield qt_class(header_type,
                           stream.read(),
                           base_offset)
        else:
            yield qt_class(header_type,
                           stream.read(header_size - 8),
                           base_offset)
        base_offset += header_size

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
    if (qt_atom.type is None):
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

def __remove_qt_atom__(qt_atom, atom_name):
    if (qt_atom.type is None):
        return "".join(
            [__remove_qt_atom__(a, atom_name) for a in qt_atom])
    elif (qt_atom.type == atom_name):
        return ""
    else:
        if (not qt_atom.is_container()):
            return __build_qt_atom__(qt_atom.type,qt_atom.data)
        else:
            return __build_qt_atom__(qt_atom.type,
                                     "".join(
                    [__remove_qt_atom__(a,atom_name) for a in qt_atom]))


class __M4AAudio_faac__(AudioFile):
    SUFFIX = "m4a"
    NAME = SUFFIX
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
            raise InvalidFile(_(u'Required moov atom not found'))

    @classmethod
    def is_type(cls, file):
        header = file.read(12)

        if ((header[4:8] == 'ftyp') and
            (header[8:12] in ('mp41','mp42','M4A ','M4B '))):
            file.seek(0,0)
            atoms = __Qt_Atom_Stream__(file)
            try:
                return atoms['moov']['trak']['mdia']['minf']['stbl']['stsd'].data[12:16] == 'mp4a'
            except KeyError:
                return False

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
        f = file(self.filename,'rb')
        try:
            qt_stream = __Qt_Atom_Stream__(f)
            try:
                meta_atom = ATOM_META.parse(
                    qt_stream['moov']['udta']['meta'].data)
            except KeyError:
                return None

            for atom in meta_atom.atoms:
                if (atom.type == 'ilst'):
                    return M4AMetaData([
                            __ILST_Atom__(
                                type=ilst_atom.type,
                                sub_atoms=[__Qt_Atom__(type=sub_atom.type,
                                                       data=sub_atom.data,
                                                       offset=0)
                                           for sub_atom in ilst_atom.data])
                            for ilst_atom in ATOM_ILST.parse(atom.data)])
            else:
                return None
        finally:
            f.close()

    def set_metadata(self, metadata):
        metadata = M4AMetaData.converted(metadata)
        if (metadata is None): return

        old_metadata = self.get_metadata()
        if (old_metadata is not None):
            if ('----' in old_metadata.keys()):
                metadata['----'] = old_metadata['----']
            if ('=A9too'.decode('quopri') in old_metadata.keys()):
                metadata['=A9too'.decode('quopri')] = \
                    old_metadata['=A9too'.decode('quopri')]

        #this is a two-pass operation
        #first we replace the contents of the moov->udta->meta atom
        #with our new metadata
        #this may move the 'mdat' atom, so we must go back
        #and update the contents of
        #moov->trak->mdia->minf->stbl->stco
        #with new offset information

        stco = ATOM_STCO.parse(
           self.qt_stream['moov']['trak']['mdia']['minf']['stbl']['stco'].data)

        mdat_offset = stco.offset[0] - self.qt_stream['mdat'].offset

        new_file = __Qt_Atom_Stream__(cStringIO.StringIO(
                __replace_qt_atom__(self.qt_stream,
                                    metadata.to_atom(
                        self.qt_stream['moov']['udta']['meta']))))

        mdat_offset = new_file['mdat'].offset + mdat_offset

        stco.offset = [x - stco.offset[0] + mdat_offset
                       for x in stco.offset]

        new_file = __replace_qt_atom__(new_file,
                                       __Qt_Atom__('stco',
                                                   ATOM_STCO.build(stco),
                                                   0))

        f = file(self.filename,"wb")
        f.write(new_file)
        f.close()

        f = file(self.filename,"rb")
        self.qt_stream = __Qt_Atom_Stream__(f)

    def delete_metadata(self):
        self.set_metadata(MetaData())


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
    def from_pcm(cls, filename, pcmreader,compression="100"):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.channels > 2):
            pcmreader = PCMConverter(pcmreader,
                                     sample_rate=pcmreader.sample_rate,
                                     channels=2,
                                     bits_per_sample=pcmreader.bits_per_sample)

        #faac requires files to end with .m4a for some reason
        if (not filename.endswith(".m4a")):
            import tempfile
            actual_filename = filename
            tempfile = tempfile.NamedTemporaryFile(suffix=".m4a")
            filename = tempfile.name
        else:
            actual_filename = tempfile = None

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
                               stdout=devnull,
                               preexec_fn=ignore_sigint)
        #Note: faac handles SIGINT on its own,
        #so trying to ignore it doesn't work like on most other encoders.

        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()

        if (sub.wait() == 0):
            if (tempfile is not None):
                filename = actual_filename
                f = file(filename,'wb')
                tempfile.seek(0,0)
                transfer_data(tempfile.read,f.write)
                f.close()
                tempfile.close()

            return M4AAudio(filename)
        else:
            if (tempfile is not None):
                tempfile.close()
            raise EncodingError(BIN['faac'])

    @classmethod
    def can_add_replay_gain(cls):
        #return BIN.can_execute(BIN['aacgain'])
        return False

    @classmethod
    def lossless_replay_gain(cls):
        return False

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]

        #helpfully, aacgain is flag-for-flag compatible with mp3gain
        if ((len(track_names) > 0) and (BIN.can_execute(BIN['aacgain']))):
            devnull = file(os.devnull,'ab')
            sub = subprocess.Popen([BIN['aacgain'],'-k','-q','-r'] + \
                                       track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()

            devnull.close()

class __M4AAudio_nero__(__M4AAudio_faac__):
    DEFAULT_COMPRESSION = "0.5"
    COMPRESSION_MODES = ("0.0","0.1","0.2","0.3","0.4","0.5",
                         "0.6","0.7","0.8","0.9","1.0")
    BINARIES = ("neroAacDec","neroAacEnc")

    def to_pcm(self):
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            self.to_wave(f.name)
            f.seek(0,0)
            return TempWaveReader(f)
        except EncodingError:
            return PCMReaderError(None,
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  bits_per_sample=self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        import tempfile
        tempwavefile = tempfile.NamedTemporaryFile(suffix=".wav")
        if (pcmreader.sample_rate > 96000):
            tempwave = WaveAudio.from_pcm(
                tempwavefile.name,
                PCMConverter(pcmreader,
                             sample_rate=96000,
                             channels=pcmreader.channels,
                             bits_per_sample=pcmreader.bits_per_sample))
        else:
            tempwave = WaveAudio.from_pcm(
                tempwavefile.name,
                pcmreader)

        cls.__from_wave__(filename,tempwave.filename,compression)
        tempwavefile.close()
        return cls(filename)

    def to_wave(self, wave_file):
        devnull = file(os.devnull,"w")
        try:
            sub = subprocess.Popen([BIN["neroAacDec"],
                                    "-if",self.filename,
                                    "-of",wave_file],
                                   stderr=devnull)
            if (sub.wait() != 0):
                raise EncodingError()
        finally:
            devnull.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        wave = open(wave_filename)
        if (wave.sample_rate > 96000):
            #convert through PCMConverter if sample rate is too high
            import tempfile
            tempwavefile = tempfile.NamedTemporaryFile(suffix=".wav")
            tempwave = WaveAudio.from_pcm(
                tempwavefile.name,
                PCMConverter(wave.to_pcm(),
                             sample_rate=96000,
                             channels=wave.channels(),
                             bits_per_sample=wave.bits_per_sample()))
            return cls.__from_wave__(filename,tempwave.filename,compression)
            tempwavefile.close()
        else:
            return cls.__from_wave__(filename,wave_filename,compression)

    @classmethod
    def __from_wave__(cls, filename, wave_filename, compression):
        devnull = file(os.devnull,"w")
        try:
            sub = subprocess.Popen([BIN["neroAacEnc"],
                                    "-q",compression,
                                    "-if",wave_filename,
                                    "-of",filename],
                                   stdout=devnull,
                                   stderr=devnull)

            if (sub.wait() != 0):
                raise EncodingError(BIN['neroAacEnc'])
            else:
                return cls(filename)
        finally:
            devnull.close()

if (BIN.can_execute(BIN["neroAacEnc"]) and
    BIN.can_execute(BIN["neroAacDec"])):
    M4AAudio = __M4AAudio_nero__
else:
    M4AAudio = __M4AAudio_faac__

#This is an ILST sub-atom, which itself is a container for other atoms.
#For human-readable fields, those will contain a single DATA sub-atom
#containing the data itself.
#For instance:
#
#'ilst' atom
#  |
#  +-'\xa9nam' atom
#        |
#        +-'data' atom
#            |
#            +-'\x00\x00\x00\x01\x00\x00\x00\x00Track Name' data
class __ILST_Atom__:
    #type is a string
    #sub_atoms is a list of __Qt_Atom__-compatible sub-atom objects
    def __init__(self, type, sub_atoms):
        self.type = type
        self.data = sub_atoms

    def __eq__(self, o):
        if (hasattr(o,"type") and
            hasattr(o,"data")):
            return ((self.type == o.type) and
                    (self.data == o.data))
        else:
            return False

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return "__ILST_Atom__(%s,%s)" % (repr(self.type),
                                         repr(self.data))

    def __unicode__(self):
        for atom in self.data:
            if (atom.type == 'data'):
                if (atom.data.startswith('0000000100000000'.decode('hex'))):
                    return atom.data[8:].decode('utf-8')
                elif (self.type == 'trkn'):
                    trkn = ATOM_TRKN.parse(atom.data[8:])
                    if (trkn.total_tracks > 0):
                        return u"%d/%d" % (trkn.track_number,
                                           trkn.total_tracks)
                    else:
                        return unicode(trkn.track_number)
                elif (self.type == 'disk'):
                    disk = ATOM_DISK.parse(atom.data[8:])
                    if (disk.total_disks > 0):
                        return u"%d/%d" % (disk.disk_number,
                                           disk.total_disks)
                    else:
                        return unicode(disk.disk_number)
                else:
                    if (len(atom.data) > 28):
                        return unicode(atom.data[8:20].encode('hex').upper()) + u"\u2026"
                    else:
                        return unicode(atom.data[8:].encode('hex'))
        else:
            return u""

    def __str__(self):
        for atom in self.data:
            if (atom.type == 'data'):
                return atom.data
        else:
            return ""

class M4AMetaData(MetaData,dict):
                                                   # iTunes ID:
    ATTRIBUTE_MAP = {
        'track_name':'=A9nam'.decode('quopri'),    # Name
        'artist_name':'=A9ART'.decode('quopri'),   # Artist
        'year':'=A9day'.decode('quopri'),          # Year
        'performer_name':'aART',                   # Album Artist
        'track_number':'trkn',                     # Track Number
        'track_total':'trkn',
        'album_name':'=A9alb'.decode('quopri'),    # Album
        'album_number':'disk',                     # Disc Number
        'album_total':'disk',
        #?:'=A9grp'.decode('quopri')               # Grouping
        #?:'tmpo'                                  # BPM
        'composer_name':'=A9wrt'.decode('quopri'), # Composer
        'comment':'=A9cmt'.decode('quopri'),       # Comments
        'copyright':'cprt'}                        # (not listed)
        #'artist_name':'=A9com'.decode('quopri')}

    def __init__(self, ilst_atoms):
        dict.__init__(self)
        for ilst_atom in ilst_atoms:
            self.setdefault(ilst_atom.type,[]).append(ilst_atom)

    #takes an atom type string
    #and a binary string object
    #returns an appropriate __ILST_Atom__ list
    #suitable for adding to our internal dictionary
    @classmethod
    def binary_atom(cls, key, value):
        return [__ILST_Atom__(key,
                              [__Qt_Atom__(
                        "data",
                        value,
                        0)])]

    #takes an atom type string
    #and a unicode text object
    #returns an appropriate __ILST_Atom__ list
    #suitable for adding to our internal dictionary
    @classmethod
    def text_atom(cls, key, text):
        return cls.binary_atom(key,'0000000100000000'.decode('hex') + \
                                   text.encode('utf-8'))

    @classmethod
    def trkn_atom(cls, track_number, track_total):
        return cls.binary_atom('trkn',
                               '0000000000000000'.decode('hex') + \
                                   ATOM_TRKN.build(
                                       Con.Container(
                    track_number=track_number,
                    total_tracks=track_total)))

    @classmethod
    def disk_atom(cls, disk_number, disk_total):
        return cls.binary_atom('disk',
                               '0000000000000000'.decode('hex') + \
                                   ATOM_DISK.build(
                                       Con.Container(
                    disk_number=disk_number,
                    total_disks=disk_total)))

    @classmethod
    def covr_atom(cls, image_data):
        return cls.binary_atom('covr',
                               '0000000000000000'.decode('hex') + \
                                   image_data)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        if (self.ATTRIBUTE_MAP.has_key(key)):
            if (key not in MetaData.__INTEGER_FIELDS__):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.text_atom(
                    self.ATTRIBUTE_MAP[key],
                    value)

            elif (key == 'track_number'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.trkn_atom(
                    int(value),self.track_total)

            elif (key == 'track_total'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.trkn_atom(
                    self.track_number,int(value))

            elif (key == 'album_number'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.disk_atom(
                    int(value),self.album_total)

            elif (key == 'album_total'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.disk_atom(
                    self.album_number,int(value))

    def __getattr__(self, key):
        if (key == 'track_number'):
            return ATOM_TRKN.parse(
                str(self.get('trkn',[chr(0) * 16])[0])[8:]).track_number
        elif (key == 'track_total'):
            return ATOM_TRKN.parse(
                str(self.get('trkn',[chr(0) * 16])[0])[8:]).total_tracks
        elif (key == 'album_number'):
            return ATOM_DISK.parse(
                str(self.get('disk',[chr(0) * 14])[0])[8:]).disk_number
        elif (key ==  'album_total'):
            return ATOM_DISK.parse(
                str(self.get('disk',[chr(0) * 14])[0])[8:]).total_disks
        elif (key in self.ATTRIBUTE_MAP):
            return unicode(self.get(self.ATTRIBUTE_MAP[key],[u''])[0])
        elif (key in MetaData.__FIELDS__):
            return u''
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def images(self):
        try:
            return [M4ACovr(str(i)[8:]) for i in self['covr']]
        except KeyError:
            return list()

    def add_image(self, image):
        if (image.type == 0):
            self.setdefault('covr',[]).append(self.__class__.covr_atom(
                    image.data)[0])

    def delete_image(self, image):
        i = 0
        for image_atom in self.get('covr',[]):
            if (str(image_atom)[8:] == image.data):
                del(self['covr'][i])
                break

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,M4AMetaData))):
            return metadata

        m4a = M4AMetaData([])

        for (field,key) in cls.ATTRIBUTE_MAP.items():
            value = getattr(metadata,field)
            if (field not in cls.__INTEGER_FIELDS__):
                if (value != u''):
                    m4a[key] = cls.text_atom(key,value)

        if ((metadata.track_number != 0) or
            (metadata.track_total != 0)):
            m4a['trkn'] = cls.trkn_atom(metadata.track_number,
                                         metadata.track_total)

        if ((metadata.album_number != 0) or
            (metadata.album_total != 0)):
            m4a['disk'] = cls.disk_atom(metadata.album_number,
                                         metadata.album_total)

        if (len(metadata.front_covers()) > 0):
            m4a['covr'] = [cls.covr_atom(i.data)[0]
                            for i in metadata.front_covers()]

        return m4a

    def merge(self, metadata):
        metadata = self.__class__.converted(metadata)
        if (metadata is None):
            return

        for (key,values) in metadata.items():
            if ((key not in 'trkn','disk') and
                (len(values) > 0) and
                (len(self.get(key,[])) == 0)):
                self[key] = values
        for attr in ("track_number","track_total",
                     "album_number","album_total"):
            if ((getattr(self,attr) == 0) and
                (getattr(metadata,attr) != 0)):
                setattr(self,attr,getattr(metadata,attr))

    #returns the contents of this M4AMetaData as a 'meta' __Qt_Atom__ object
    def to_atom(self, previous_meta):
        previous_meta = ATOM_META.parse(previous_meta.data)

        new_meta = Con.Container(version=previous_meta.version,
                                 flags=previous_meta.flags,
                                 atoms=[])

        ilst = []
        for values in self.values():
            for ilst_atom in values:
                ilst.append(Con.Container(type=ilst_atom.type,
                                          data=[Con.Container(
                                type=sub_atom.type,
                                data=sub_atom.data)
                                                for sub_atom in ilst_atom.data]))

        for sub_atom in previous_meta.atoms:
            if (sub_atom.type == 'ilst'):
                new_meta.atoms.append(Con.Container(
                        type='ilst',
                        data=ATOM_ILST.build(ilst)))
            else:
                new_meta.atoms.append(sub_atom)

        return __Qt_Atom__(
            'meta',
            ATOM_META.build(new_meta),
            0)

    def __comment_name__(self):
        return u'M4A'

    @classmethod
    def supports_images(self):
        return True

    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {" nam":1,
                   " ART":6,
                   " com":5,
                   " alb":2,
                   "trkn":3,
                   "disk":4,
                   "----":8}

        return cmp((KEY_MAP.get(pair1[0],7),pair1[0],pair1[1]),
                   (KEY_MAP.get(pair2[0],7),pair2[0],pair2[1]))

    def __comment_pairs__(self):
        pairs = []
        for (key,values) in self.items():
            for value in values:
                pairs.append((key.replace(chr(0xA9),' '),unicode(value)))
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


class ALACAudio(M4AAudio):
    SUFFIX = "m4a"
    NAME = "alac"
    DEFAULT_COMPRESSION = ""
    COMPRESSION_MODES = ("",)
    BINARIES = ("ffmpeg",)

    BPS_MAP = {8:"u8",
               16:"s16le",
               24:"s24le"}

    @classmethod
    def is_type(cls, file):
        header = file.read(12)

        if ((header[4:8] == 'ftyp') and
            (header[8:12] in ('mp41','mp42','M4A ','M4B '))):
            file.seek(0,0)
            atoms = __Qt_Atom_Stream__(file)
            try:
                return atoms['moov']['trak']['mdia']['minf']['stbl']['stsd'].data[12:16] == 'alac'
            except KeyError:
                return False

    def lossless(self):
        return True

    def to_pcm(self):
        devnull = file(os.devnull,"ab")

        sub = subprocess.Popen([BIN['ffmpeg'],
                                "-i",self.filename,
                                "-f",self.BPS_MAP[self.__bits_per_sample__],
                                "-"],
                               stdout=subprocess.PIPE,
                               stderr=devnull,
                               stdin=devnull)
        return PCMReader(sub.stdout,
                         sample_rate=self.__sample_rate__,
                         channels=self.__channels__,
                         bits_per_sample=self.__bits_per_sample__,
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=""):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        #in a remarkable piece of half-assery,
        #ALAC only supports 16bps and 2 channels
        #anything else wouldn't be lossless,
        #and must be rejected

        if ((pcmreader.bits_per_sample != 16) or
            (pcmreader.channels != 2)):
            raise InvalidFormat(_(u"ALAC requires input files to be 16 bits-per-sample and have 2 channels"))

        devnull = file(os.devnull,"ab")

        if (not filename.endswith(".m4a")):
            import tempfile
            actual_filename = filename
            tempfile = tempfile.NamedTemporaryFile(suffix=".m4a")
            filename = tempfile.name
        else:
            actual_filename = tempfile = None

        sub = subprocess.Popen([BIN['ffmpeg'],
                                "-f",cls.BPS_MAP[pcmreader.bits_per_sample],
                                "-ar",str(pcmreader.sample_rate),
                                "-ac",str(pcmreader.channels),
                                "-i","-",
                                "-acodec","alac",
                                "-title","placeholder",
                                "-y",filename],
                               stdin=subprocess.PIPE,
                               stderr=devnull,
                               stdout=devnull)

        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()
        sub.wait()

        if (tempfile is not None):
            filename = actual_filename
            f = file(filename,'wb')
            tempfile.seek(0,0)
            transfer_data(tempfile.read,f.write)
            f.close()
            tempfile.close()

        return ALACAudio(filename)

    @classmethod
    def has_binaries(cls, system_binaries):
        if (set([True] + \
                    [system_binaries.can_execute(system_binaries[command])
                     for command in cls.BINARIES]) == set([True])):
            #if we have the ffmpeg executable,
            #ensure it has ALAC encode/decode capability

            devnull = file(os.devnull,"ab")
            ffmpeg_formats = subprocess.Popen([BIN["ffmpeg"],"-formats"],
                                              stdout=subprocess.PIPE,
                                              stderr=devnull)
            alac_ok = False
            for line in ffmpeg_formats.stdout.readlines():
                if (("alac" in line) and ("DEA" in line)):
                    alac_ok = True
            ffmpeg_formats.stdout.close()
            ffmpeg_formats.wait()

            return alac_ok


#######################
#AAC File
#######################

class ADTSException(Exception): pass

class AACAudio(AudioFile):
    SUFFIX = "aac"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "100"
    COMPRESSION_MODES = tuple(["10"] + map(str,range(50,500,25)) + ["500"])
    BINARIES = ("faac","faad")

    AAC_FRAME_HEADER = Con.BitStruct("aac_header",
                                 Con.Bits("sync",12),
                                 Con.Bits("mpeg_id",1),
                                 Con.Bits("mpeg_layer",2),
                                 Con.Flag("protection_absent"),
                                 Con.Bits("profile",2),
                                 Con.Bits("sampling_frequency_index",4),
                                 Con.Flag("private"),
                                 Con.Bits("channel_configuration",3),
                                 Con.Bits("original",1),
                                 Con.Bits("home",1),
                                 Con.Bits("copyright_identification_bit",1),
                                 Con.Bits("copyright_identification_start",1),
                                 Con.Bits("aac_frame_length",13),
                                 Con.Bits("adts_buffer_fullness",11),
                                 Con.Bits("no_raw_data_blocks_in_frame",2),
                                 Con.If(
        lambda ctx: ctx["protection_absent"] == False,
        Con.Bits("crc_check",16)))

    SAMPLE_RATES = [96000, 88200, 64000, 48000,
                    44100, 32000, 24000, 22050,
                    16000, 12000, 11025,  8000]

    def __init__(self, filename):
        self.filename = filename

        f = file(self.filename,"rb")
        try:
            header = AACAudio.AAC_FRAME_HEADER.parse_stream(f)
            f.seek(0,0)
            self.__channels__ = header.channel_configuration
            self.__bits_per_sample__ = 16  #floating point samples
            self.__sample_rate__ = AACAudio.SAMPLE_RATES[
                header.sampling_frequency_index]
            self.__frame_count__ = AACAudio.aac_frame_count(f)
        finally:
            f.close()

    @classmethod
    def is_type(cls, file):
        try:
            header = AACAudio.AAC_FRAME_HEADER.parse_stream(file)
            return ((header.sync == 0xFFF) and
                    (header.mpeg_id == 1) and
                    (header.mpeg_layer == 0))
        except:
            return False

    def bits_per_sample(self):
        return self.__bits_per_sample__

    def channels(self):
        return self.__channels__

    def lossless(self):
        return False

    def total_frames(self):
        return self.__frame_count__ * 1024

    def sample_rate(self):
        return self.__sample_rate__

    def to_pcm(self):
        devnull = file(os.devnull,"ab")

        sub = subprocess.Popen([BIN['faad'],"-t","-f",str(2),"-w",
                                self.filename],
                               stdout=subprocess.PIPE,
                               stderr=devnull)
        return PCMReader(sub.stdout,
                         sample_rate=self.__sample_rate__,
                         channels=self.__channels__,
                         bits_per_sample=self.__bits_per_sample__,
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression="100"):
        import bisect

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.sample_rate not in AACAudio.SAMPLE_RATES):
            if (pcmreader.channels > 2):
                channels = 2
            else:
                channels = pcmreader.channels

            sample_rates = list(sorted(AACAudio.SAMPLE_RATES))

            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=([sample_rates[0]] + sample_rates)[
                    bisect.bisect(sample_rates,pcmreader.sample_rate)],
                channels=channels,
                bits_per_sample=pcmreader.bits_per_sample)
        elif (pcmreader.channels > 2):
            pcmreader = PCMConverter(pcmreader,
                                     sample_rate=pcmreader.sample_rate,
                                     channels=2,
                                     bits_per_sample=pcmreader.bits_per_sample)

        #faac requires files to end with .aac for some reason
        if (not filename.endswith(".aac")):
            import tempfile
            actual_filename = filename
            tempfile = tempfile.NamedTemporaryFile(suffix=".aac")
            filename = tempfile.name
        else:
            actual_filename = tempfile = None

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
        try:
            pcmreader.close()
        except DecodingError:
            raise EncodingError()
        sub.stdin.close()

        if (sub.wait() == 0):
            if (tempfile is not None):
                filename = actual_filename
                f = file(filename,'wb')
                tempfile.seek(0,0)
                transfer_data(tempfile.read,f.write)
                f.close()
                tempfile.close()

            return AACAudio(filename)
        else:
            if (tempfile is not None):
                tempfile.close()
            raise EncodingError(BIN['faac'])

    @classmethod
    def aac_frames(cls, stream):
        while (True):
            try:
                header = AACAudio.AAC_FRAME_HEADER.parse_stream(stream)
            except Con.FieldError:
                break

            if (header.sync != 0xFFF):
                raise ADTSException(_(u"Invalid frame sync"))

            if (header.protection_absent):
                yield (header,stream.read(header.aac_frame_length - 7))
            else:
                yield (header,stream.read(header.aac_frame_length - 9))

    @classmethod
    def aac_frame_count(cls, stream):
        import sys
        total = 0
        while (True):
            try:
                header = AACAudio.AAC_FRAME_HEADER.parse_stream(stream)
            except Con.FieldError:
                break

            if (header.sync != 0xFFF):
                break

            total += 1

            if (header.protection_absent):
                stream.seek(header.aac_frame_length - 7,1)
            else:
                stream.seek(header.aac_frame_length - 9,1)

        return total

