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

import sys

if (sys.version_info < (2,4,4,'final',0)):
    print >>sys.stderr,"*** Python 2.4.4 or better required"
    sys.exit(1)

import subprocess
import re
import cStringIO
import os
import os.path
import ConfigParser
import struct

try:
    import construct as Con
except ImportError:
    try:
        import Construct as Con
    except ImportError:
        print >>sys.stderr,"*** construct module not found"
        print >>sys.stderr,"""To remedy this: \"make construct_install\"
from the audiotools source directory to install the Construct module."""
        sys.exit(1)
    



class RawConfigParser(ConfigParser.RawConfigParser):
    def get_default(self, section, option, default):
        try:
            return self.get(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

    def getint_default(self, section, option, default):
        try:
            return self.getint(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

config = RawConfigParser()
config.read([os.path.join(sys.prefix,"etc","audiotools.cfg"),
             os.path.expanduser('~/.audiotools.cfg')])

BUFFER_SIZE = 0x100000

class __system_binaries__:
    def __init__(self, config):
        self.config = config

    def __getitem__(self, command):
        try:
            return self.config.get("Binaries",command)
        except ConfigParser.NoSectionError:
            return command
        except ConfigParser.NoOptionError:
            return command

    def can_execute(self, command):
        if (os.sep in command):
            return os.access(command,os.X_OK)
        else:
            for path in os.environ.get('PATH',os.defpath).split(os.pathsep):
                if (os.access(os.path.join(path,command),os.X_OK)):
                    return True
            return False

BIN = __system_binaries__(config)

DEFAULT_CDROM = config.get_default("System","cdrom","/dev/cdrom")

FREEDB_SERVER = config.get_default("FreeDB","server","us.freedb.org")
FREEDB_PORT = config.getint_default("FreeDB","port",80)

VERSION = "2.2"

FILENAME_FORMAT = config.get_default(
    "Filenames","format",
    '%(track_number)2.2d - %(track_name)s.%(suffix)s')

FS_ENCODING = sys.getfilesystemencoding()
if (FS_ENCODING == None):
    FS_ENCODING = 'UTF-8'
IO_ENCODING = "UTF-8"

try:
    import cpucount
    MAX_CPUS = cpucount.cpucount()
except ImportError:
    MAX_CPUS = 1

if (config.has_option("System","maximum_jobs")):
    MAX_JOBS = config.getint_default("System","maximum_jobs",1)
else:
    MAX_JOBS = MAX_CPUS

BIG_ENDIAN = (struct.pack("=I",0x100) == struct.pack(">I",0x100))

#raised by open() if the file cannot be identified or opened correctly
class UnsupportedFile(Exception): pass

#raised if an audio file cannot be initialized correctly
class InvalidFile(Exception): pass

#raised if an audio file cannot be created correctly from from_pcm() 
class InvalidFormat(Exception): pass

#takes a filename string
#returns a valid AudioFile object based on the file data or extension
#or raises UnsupportedFile if it's not a file we support
def open(filename):
    available_types = frozenset(TYPE_MAP.values())

    try:
        f = file(filename)
    except IOError:
        raise UnsupportedFile(filename)
    try:
        for audioclass in TYPE_MAP.values():
            f.seek(0,0)
            if (audioclass.is_type(f)):
                return audioclass(filename)
        else:
            raise UnsupportedFile(filename)

    finally:
        f.close()

#takes a list of filenames
#returns a list of AudioFile objects, sorted by track_number()
#any unsupported files are filtered out
def open_files(filename_list, sorted=True):
    toreturn = []
    for filename in filename_list:
        try:
            toreturn.append(open(filename))
        except UnsupportedFile:
            pass
        except InvalidFile,msg:
            print >>sys.stderr,"*** %s: %s" % (filename,msg)

    if (sorted):
        toreturn.sort(lambda x,y: cmp(x.track_number(),
                                      y.track_number()))
    return toreturn

#a class that generates PCM audio data
#sample rate, channels and bits per sample are variable
#the data is assumed to be signed, little-endian as generated by WAV files
class PCMReader:
    def __init__(self, file,
                 sample_rate, channels, bits_per_sample,
                 process=None):
        self.file = file
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.process = process

    def read(self, bytes):
        return self.file.read(bytes)

    def close(self):
        if (self.process != None):
            self.process.wait()
        self.file.close()


#sends BUFFER_SIZE strings from from_function to to_function
#until the string is empty
def transfer_data(from_function, to_function):
    s = from_function(BUFFER_SIZE)
    while (len(s) > 0):
        to_function(s)
        s = from_function(BUFFER_SIZE)

class __capped_stream_reader__:
    #allows a maximum number of bytes "length" to
    #be read from file-like object "stream"
    #(used for reading IFF chunks)
    def __init__(self, stream, length):
        self.stream = stream
        self.remaining = length

    def read(self, bytes):
        data = self.stream.read(min(bytes,self.remaining))
        self.remaining -= len(data)
        return data

    def close(self):
        self.stream.close()


class WaveReader(PCMReader):
    #wave_file should be a file-like stream of wave data
    def __init__(self, wave_file,
                 sample_rate, channels, bits_per_sample,
                 process = None):

        self.file = wave_file
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.process = process

        #build a capped reader for the data chunk
        header = WaveAudio.WAVE_HEADER.parse_stream(self.file)
        if ((header.wave_id != 'RIFF') or
            (header.riff_type != 'WAVE')):
            raise ValueError('invalid WAVE file')

        #this won't be pretty for a WAVE file missing a 'data' chunk
        #but those are seriously invalid anyway
        chunk_header = WaveAudio.CHUNK_HEADER.parse_stream(self.file)
        while (chunk_header.chunk_id != 'data'):
            #self.file.seek(chunk_header.chunk_length,1)
            self.file.read(chunk_header.chunk_length)
            chunk_header = WaveAudio.CHUNK_HEADER.parse_stream(self.file)

        #build a reader which reads no further than the 'data' chunk
        self.wave = __capped_stream_reader__(self.file,
                                             chunk_header.chunk_length)

    def read(self, bytes):
        return self.wave.read(bytes)

    def close(self):
        self.wave.close()
        if (self.process != None):
            self.process.wait()

class TempWaveReader(WaveReader):
    def __init__(self, tempfile):
        wave = WaveAudio(tempfile.name)
        WaveReader.__init__(self,
                            tempfile,
                            sample_rate = wave.sample_rate(),
                            channels = wave.channels(),
                            bits_per_sample = wave.bits_per_sample())
        self.tempfile = tempfile

    def close(self):
        WaveReader.close(self)
        self.tempfile.close()


#takes a wave-compatible object with a readframes() method
#maps it to something PCMReader compatible
class FrameReader(PCMReader):
    def __init__(self, framefile, 
                 sample_rate, channels, bits_per_sample,
                 process=None):
        PCMReader.__init__(self,
                           file=framefile,
                           sample_rate=sample_rate, 
                           channels=channels, 
                           bits_per_sample=bits_per_sample,
                           process=process)
        self.framefile = framefile
        self.bytes_per_sample = framefile.getnchannels() * \
                                framefile.getsampwidth()

    def read(self, bytes):
        return self.framefile.readframes(bytes / self.bytes_per_sample)

    def close(self):
        self.framefile.close()
        

#returns True if the PCM data in pcmreader1 equals pcmreader2
#False if there is any data mismatch
#the readers must be closed independently of this checker
def pcm_cmp(pcmreader1, pcmreader2):
    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return False

    #rather than do byte-per-byte comparisons,
    #we'll do a length/shasum comparison
    #since pcmreader.read() doesn't necessarily
    #return BUFFER_SIZE number of bytes per read
    import sha

    data1 = sha.new()
    data2 = sha.new()
    len1 = 0
    len2 = 0

    d = pcmreader1.read(BUFFER_SIZE)
    while (len(d) > 0):
        data1.update(d)
        len1 += len(d)
        d = pcmreader1.read(BUFFER_SIZE)

    d = pcmreader2.read(BUFFER_SIZE)
    while (len(d) > 0):
        data2.update(d)
        len2 += len(d)
        d = pcmreader2.read(BUFFER_SIZE)

    return ((len1 == len2) and (data1.digest() == data2.digest()))

#returns True if the PCM data in pcmreader1 equals pcmreader2
#not counting any 0x00 bytes at the beginning and end
#of each reader
def stripped_pcm_cmp(pcmreader1, pcmreader2):
    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return False

    import sha

    data = cStringIO.StringIO()
    
    d = pcmreader1.read(BUFFER_SIZE)
    while (len(d) > 0):
        data.write(d)
        d = pcmreader1.read(BUFFER_SIZE)

    sum1 = sha.new(data.getvalue().strip(chr(0x00)))

    data = cStringIO.StringIO()
    
    d = pcmreader2.read(BUFFER_SIZE)
    while (len(d) > 0):
        data.write(d)
        d = pcmreader2.read(BUFFER_SIZE)
    
    sum2 = sha.new(data.getvalue().strip(chr(0x00)))

    del(data)

    return sum1.digest() == sum2.digest()

#######################
#Generic MetaData
#######################

class MetaData:
    #track_name, album_name and artist_name should be unicode strings
    #track_number should be an integer
    def __init__(self,
                 track_name=u"",    #the name of this individual track
                 track_number=0,    #the number of this track
                 album_name=u"",    #the name of the album this track belongs to
                 artist_name=u"",   #the song's original creator/composer
                 performer_name=u"",#the song's performing artist
                 copyright=u"",     #the song's copyright information
                 year=u""           #the album's release year
                 ):
        #we're avoiding self.foo = foo because
        #__setattr__ might need to be redefined
        #which could lead to unwelcome side-effects
        self.__dict__['track_name'] = track_name
        self.__dict__['track_number'] = track_number
        self.__dict__['album_name'] = album_name
        self.__dict__['artist_name'] = artist_name
        if (performer_name != u''):
            self.__dict__['performer_name'] = performer_name
        else:
            self.__dict__['performer_name'] = artist_name

        self.__dict__['copyright'] = copyright
        self.__dict__['year'] = year

    def __repr__(self):
        return "MetaData(%s,%s,%s,%s,%s,%s,%s)" % \
               (repr(self.track_name),
                repr(self.track_number),
                repr(self.album_name),
                repr(self.artist_name),
                repr(self.performer_name),
                repr(self.copyright),
                repr(self.year))

    #returns the type of comment this is, as a unicode string
    def __comment_name__(self):
        return u'MetaData'

    #returns a list of (key,value) tuples
    def __comment_pairs__(self):
        return zip(("Title","Artist","Performer","Album",
                    "Number","Year","Copyright"),
                   (self.track_name,
                    self.artist_name,
                    self.performer_name,
                    self.album_name,
                    str(self.track_number),
                    self.year,
                    self.copyright))

    def __unicode__(self):
        comment_pairs = self.__comment_pairs__()
        if (len(comment_pairs) > 0):
            max_key_length = max([len(pair[0]) for pair in comment_pairs])
            line_template = u"%%(key)%(length)d.%(length)ds : %%(value)s" % \
                            {"length":max_key_length}

            return unicode(os.linesep.join(
                [u"%s Comment:" % (self.__comment_name__())] + \
                [line_template % {"key":key,"value":value} for
                 (key,value) in comment_pairs]))
        else:
            return u""

    def __eq__(self, metadata):
        import operator
        
        if (metadata != None):
            return reduce(operator.and_,
                          [(getattr(self,attr) == getattr(metadata,attr))
                           for attr in
                           ("track_name","artist_name","performer_name",
                            "album_name","track_number","year",
                            "copyright")],True)
        else:
            return False

    def __ne__(self, metadata):
        return not self.__eq__(metadata)

    #takes a MetaData-compatible object (or None)
    #returns a new MetaData subclass with the data fields converted
    #or None if metadata is None or conversion isn't possible
    #For instance, VorbisComment.converted() returns a VorbisComment
    #class.  This way, AudioFiles can offload metadata conversions.
    @classmethod
    def converted(cls, metadata):
        return metadata

class AlbumMetaData(dict):
    def __init__(self, metadata_iter):
        dict.__init__(self,
                      dict([(m.track_number,m) for m in
                            metadata_iter]))

#######################
#XMCD
#######################

class XMCDException(Exception): pass

#takes an XMCD file name
#returns an AlbumMetaData-compatible object
def parse_xmcd_file(filename):
    import codecs,re,StringIO

    def split_line(line):
        if ' / ' in line:
            return line.split(' / ',1)
        else:
            return [None,line]

    file = codecs.open(filename,"r","utf-8")
    entries = {}
    VALID_LINE = re.compile(r'^[A-Z0-9]+=.*')
    TRACK_LINE = re.compile(r'^TTITLE[0-9]+$')
    try:
        try:
            lines = file.readlines()
        except UnicodeDecodeError:
            try:
                file.close()
                file = codecs.open(filename,"r","ISO-8859-1")
                lines = file.readlines()
            except UnicodeDecodeError:
                raise XMCDException(filename)

        if ((len(lines) < 1) or (not lines[0].startswith("# xmcd"))):
            raise XMCDException(filename)
        else:
            for (prefix,suffix) in [line.split('=',1)
                                    for line in lines if
                                    VALID_LINE.match(line)]:
                entries.setdefault(prefix,StringIO.StringIO()).write(
                    suffix.rstrip('\n\r'))
            entries = dict([(key,value.getvalue()) for key,value in
                            entries.items()])

            (artist_name,
             album_name) = split_line(entries.get('DTITLE',u''))

            metadata = []
            for (track_number,track_artist,track_name) in \
                [[int(key[len('TTITLE'):]) + 1,] +
                 split_line(value) for (key,value) in entries.items()
                 if TRACK_LINE.match(key)]:

                if (track_artist == None):
                    metadata.append(
                        MetaData(track_name=track_name,
                                 track_number=track_number,
                                 album_name=album_name,
                                 artist_name=artist_name,
                                 performer_name=u'',
                                 copyright=u'',
                                 year=entries.get('DYEAR',u'')))
                else:
                    metadata.append(
                        MetaData(track_name=track_name,
                                 track_number=track_number,
                                 album_name=album_name,
                                 artist_name=track_artist,
                                 performer_name=u'',
                                 copyright=u'',
                                 year=entries.get('DYEAR',u'')))
            
            return AlbumMetaData(metadata)
            
    finally:
        file.close()

#takes a list of AudioFile-compatible objects
#and, optionally, a DiscID object
#returns an XMCD file as a string
def build_xmcd_file(audiofiles, discid=None):
    import StringIO
    
    #stream is a file-like object
    #key is a string
    #value is a unicode string
    #writes as many UTF-8 encoded strings as necessary
    #to "stream" to represent the key/pair
    #while keeping below a certain number of characters per line
    def build_key_pair(stream, key, value):
        line = (u"%s=%s" % (key,value)).encode('utf-8')
        if (len(line) <= 78):  #our encoded line is short enough to fit
            print >>stream,line
        else:                   #too long when encoded, so split value
            line = cStringIO.StringIO()
            to_encode = StringIO.StringIO(value)
            try:
                line.write("%s=" % (key))
                while (len(line.getvalue()) <= 78):
                    #encode all that will fit on a line
                    #1 unicode character at a time
                    #(so that we don't split a character when encoded)
                    c = to_encode.read(1)
                    if (len(c) == 1):
                        line.write(c.encode('utf-8'))
                    else:
                        print >>stream,line.getvalue()
                        break
                else: #if there's still more to encode, do it recursively
                    print >>stream,line.getvalue()
                    build_key_pair(stream, key, to_encode.read())
            finally:
                line.close()
                to_encode.close()
                
    
    audiofiles = sorted(audiofiles,
                        lambda x,y: cmp(x.track_number(),
                                        y.track_number()))

    xmcd = StringIO.StringIO()
    print >>xmcd,"# xmcd"
    print >>xmcd,"#"
    print >>xmcd,"# Track frame offsets:"

    if (discid == None):
        offset = 150
        for track in audiofiles:
            print >>xmcd,"#\t%d" % (offset)
            offset += track.length()
        disc_length = offset / 75

        print >>xmcd,"#"
        print >>xmcd,"# Disc length: %d seconds" % (disc_length)
        print >>xmcd,"#"
        build_key_pair(xmcd,"DISCID",str(DiscID([f.length() for f in
                                                 audiofiles])))
    else:
        for offset in discid.offsets():
            print >>xmcd,"#\t%d" % (offset)
        print >>xmcd,"#"
        print >>xmcd,"# Disc length: %d seconds" % (discid.length() / 75)
        print >>xmcd,"#"
        build_key_pair(xmcd,"DISCID",str(discid))

    album_list = [file.get_metadata().album_name
                  for file in audiofiles if
                  file.get_metadata() != None]
    
    artist_list = [file.get_metadata().artist_name
                   for file in audiofiles if
                   file.get_metadata() != None]

    if (len(album_list) > 0):
        album = __most_numerous__(album_list)
    else:
        album = u""

    if (len(artist_list) > 0):
        artist =  __most_numerous__(artist_list)
    else:
        artist = u""

    build_key_pair(xmcd,"DTITLE",u"%s / %s" % (artist,album))
    build_key_pair(xmcd,"DYEAR",u"")
    
    for (i,track) in enumerate(audiofiles):
        metadata = track.get_metadata()
        if (metadata != None):
            if (metadata.artist_name != artist):
                build_key_pair(xmcd,"TTITLE%d" % (i),
                               u"%s / %s" % (metadata.artist_name,
                                             metadata.track_name))
            else:
                build_key_pair(xmcd,"TTITLE%d" % (i),
                               metadata.track_name)
                
    build_key_pair(xmcd,"EXTDD",u"")
    for (i,track) in enumerate(audiofiles):
        build_key_pair(xmcd,"EXTT%d" % (i),u"")

    build_key_pair(xmcd,"PLAYORDER",u"")
    
    return xmcd.getvalue()
    

#returns the value in item_list which occurs most often
def __most_numerous__(item_list):
    counts = {}

    for item in item_list:
        counts.setdefault(item,[]).append(item)

    return sorted([(item,len(counts[item])) for item in counts.keys()],
                  lambda x,y: cmp(x[1],y[1]))[-1][0]


#######################
#FREEDB
#######################

class DiscID:
    DISCID = Con.Struct('discid',
                        Con.UBInt8('digit_sum'),
                        Con.UBInt16('length'),
                        Con.UBInt8('track_count'))

    #tracks is a list of track lengths in CD frames
    #offsets, if present, is a list of track offsets in CD frames
    #length, if present, is the length of the entire disc in CD frames
    #lead_in is the location of the first track on the CD, in frames
    def __init__(self, tracks=[],
                 offsets=None, length=None, lead_in=150):
        self.tracks = tracks
        self.__offsets__ = offsets
        self.__length__ = length
        self.__lead_in__ = lead_in

    def add(self, track):
        self.tracks.append(track)

    def offsets(self):
        if (self.__offsets__ == None):
            offsets = [150]
            
            for track in self.tracks[0:-1]:
                offsets.append(track + offsets[-1])
                
            return offsets
        else:
            return self.__offsets__

    def length(self):
        if (self.__length__ == None):
            return sum(self.tracks)
        else:
            return self.__length__

    def idsuffix(self):
        return str(len(self.tracks)) + " " + \
               " ".join([str(offset) for offset in self.offsets()]) + \
               " " + str((self.length() + self.__lead_in__) / 75)
    
    def __str__(self):
        def __count_digits__(i):
            if (i == 0):
                return 0
            else:
                return (i % 10) + __count_digits__(i / 10)

        disc_id = Con.Container()
        
        disc_id.track_count = len(self.tracks)
        disc_id.length = self.length() / 75
        disc_id.digit_sum = sum([__count_digits__(o / 75) 
                                 for o in self.offsets()]) % 0xFF

        return DiscID.DISCID.build(disc_id).encode('hex')
        
    def freedb_id(self):
        return str(self) + " " + self.idsuffix()

    def toxmcd(self, output):
        output.write(build_xmcd_file(
            [DummyAudioFile(length,None) for length in self.tracks],
            self))

class FreeDBException(Exception): pass

class FreeDB:
    LINE = re.compile(r'\d\d\d\s.+')
    
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.socket = None
        self.r = None
        self.w = None

    def connect(self):
        import socket
        
        try:
            print >>sys.stderr,"* Connecting to \"%s\"" % (self.server)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server,self.port))
            
            self.r = self.socket.makefile("rb")
            self.w = self.socket.makefile("wb")
            
            (code,msg) = self.read()  #the welcome message
            if (code == 201):
                print >>sys.stderr,"* Connected ... attempting to login"
            else:
                self.r.close()
                self.w.close()
                self.socket.close()
                raise FreeDBException("Invalid Hello Message")
            
            self.write("cddb hello user %s %s %s" % \
                       (socket.getfqdn(),"audiotools",VERSION))

            (code,msg) = self.read()  #the handshake successful message
            if (code != 200):
                self.r.close()
                self.w.close()
                self.socket.close()
                raise FreeDBException("Handshake unsuccessful")
            
            self.write("proto 6")
            
            (code,msg) = self.read()  #the protocol successful message
            if ((code != 200) and (code != 201)):
                self.r.close()
                self.w.close()
                self.socket.close()
                raise FreeDBException("Protocol change unsuccessful")
            
        except socket.error,err:
            raise FreeDBException(err[1])

    def close(self):
        print >>sys.stderr,"* Closing connection"
        
        self.write("quit")
        (code,msg) = self.read()  #the quit successful message
        
        self.r.close()
        self.w.close()
        self.socket.close()

    def write(self, line):
        if (self.socket != None):
            self.w.write(line)
            self.w.write("\r\n")
            self.w.flush()

    def read(self):
        line = self.r.readline()
        if (FreeDB.LINE.match(line)):
            return (int(line[0:3]),line[4:].rstrip("\r\n"))
        else:
            return (None,line.rstrip("\r\n"))

    def query(self, disc_id):
        matches = []

        print >>sys.stderr,"* Sending ID to server"
        
        self.write("cddb query " + disc_id.freedb_id())
        (code,msg) = self.read()
        if (code == 200):
            matches.append(msg)
        elif ((code == 211) or (code == 210)):
            while (msg != "."):
                (code,msg) = self.read()
                if (msg != "."):
                    matches.append(msg)

        if (len(matches) == 1):
            print >>sys.stderr,"* 1 match found"
        else:
            print >>sys.stderr,"* %s matches found" % (len(matches))

        return map(lambda m: m.split(" ",2), matches)

    #category and id are raw strings, as returned by query()
    #output is a file handle the output will be written to
    def read_data(self, category, id, output):
        self.write("cddb read " + category + " " + id)
        (code,msg) = self.read()
        if (code == 210):
            line = self.r.readline()
            while (line.strip() != "."):
                output.write(line)
                line = self.r.readline()
        else:
            print >>sys.stderr,(code,msg)



class FreeDBWeb(FreeDB):
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.connection = None

    def connect(self):
        import httplib
        
        self.connection = httplib.HTTPConnection(self.server,self.port)
        
    def close(self):
        if (self.connection != None):
            self.connection.close()

    def write(self, line):
        import urllib,socket
        
        u = urllib.urlencode({"hello":"user %s %s %s" % \
                                      (socket.getfqdn(),"audiotools",VERSION),
                              "proto":str(6),
                              "cmd":line})

        self.connection.request("POST", 
                                "/~cddb/cddb.cgi", 
                                u, 
                                {"Content-type":"application/x-www-form-urlencoded",
                                 "Accept": "text/plain"})

    def read(self):
        response = self.connection.getresponse()
        return response.read()

    def __parse_line__(self, line):
        if (FreeDB.LINE.match(line)):
            return (int(line[0:3]),line[4:].rstrip("\r\n"))
        else:
            return (None,line.rstrip("\r\n"))
            
    def query(self, disc_id):
        matches = []

        print >>sys.stderr,"* Sending ID to server"
        
        self.write("cddb query " + disc_id.freedb_id())
        data =  cStringIO.StringIO(self.read())
        (code,msg) = self.__parse_line__(data.readline())
        if (code == 200):
            matches.append(msg)
        elif ((code == 211) or (code == 210)):
            while (msg != "."):
                (code,msg) = self.__parse_line__(data.readline())
                if (msg != "."):
                    matches.append(msg)

        if (len(matches) == 1):
            print >>sys.stderr,"* 1 match found"
        else:
            print >>sys.stderr,"* %s matches found" % (len(matches))

        return map(lambda m: m.split(" ",2), matches)
        
    #category and id are raw strings, as returned by query()
    #output is a file handle the output will be written to
    def read_data(self, category, id, output):
        self.write("cddb read " + category + " " + id)
        data = cStringIO.StringIO(self.read())
        (code,msg) = self.__parse_line__(data.readline())
        if (code == 210):
            line = data.readline()
            while (line.strip() != "."):
                output.write(line)
                line = data.readline()
        else:
            print >>sys.stderr,(code,msg)
    

#matches is a list of (category,disc_id,title) tuples returned from
#FreeDB.query().  If the length of that list is 1, return the first
#item.  If the length is greater than one, present the user a list of
#choices and force him/her to pick the closest match for the CD.
#That data can then be sent to FreeDB.read_data()
def __select_match__(matches):
    if (len(matches) == 1):
        return matches[0]
    elif (len(matches) < 1):
        return None
    else:
        print >>sys.stderr,"Please Select the Closest Match:"
        selected = 0
        while ((selected < 1) or (selected > len(matches))):
            for i in range(len(matches)):
                print >>sys.stderr,\
                  "%s) [%s] %s" % (i + 1, matches[i][0],matches[i][2])
            try:
                sys.stderr.write("Your Selection [1-%s]:" % (len(matches)))
                sys.stderr.flush()
                selected = int(sys.stdin.readline().strip())
            except ValueError:
                selected = 0

        return matches[selected - 1]

#takes a DiscID value and a file handle for output
#and runs the entire FreeDB querying sequence
#the file handle is closed at the conclusion of this function
def get_xmcd(disc_id, output, freedb_server, freedb_server_port):
    try:
        freedb = FreeDBWeb(freedb_server,freedb_server_port)
        freedb.connect()
    except FreeDBException,msg:
        #if an exception occurs during the opening,
        #freedb will auto-close its sockets
        print >>sys.stderr,"* Error: %s" % (msg)
        output.close()
        print >>sys.stderr,"* %s written" % (output.name)
        return
        
    try:
        matches = freedb.query(disc_id)
        #HANDLE MULTIPLE MATCHES, or NO MATCHES
        if (len(matches) > 0):
            (category,idstring,title) = __select_match__(matches)
            freedb.read_data(category,idstring,output)
        else:
            disc_id.toxmcd(output)
        
        freedb.close()
    except FreeDBException,msg:
        #otherwise, close the sockets manually
        print >>sys.stderr,"* Error: %s" % (msg)
        freedb.close()
        
    output.close()
    print >>sys.stderr,"* %s written" % (output.name)


#######################
#Generic Audio File
#######################

class NotYetImplemented(Exception): pass

class AudioFile:
    SUFFIX = ""
    DEFAULT_COMPRESSION = ""
    COMPRESSION_MODES = ("",)
    BINARIES = tuple()

    def __init__(self, filename):
        self.filename = filename

    #takes a seekable file pointer rewound to the start of the file
    #returns True if that header describes this format
    #returns False if not
    @classmethod
    def is_type(cls, file):
        return False

    def bits_per_sample(self):
        raise NotYetImplemented()

    def channels(self):
        raise NotYetImplemented()

    def lossless(self):
        raise NotYetImplemented()

    def set_metadata(self, metadata):
        pass

    def get_metadata(self):
        return None

    def total_samples(self):
        raise NotYetImplemented()

    #returns the length of the audio in CD frames (1/75 of a second)
    def length(self):
        try:
            return (self.total_samples() * 75) / self.sample_rate()
        except ZeroDivisionError:
            return 0

    def sample_rate(self):
        raise NotYetImplemented()


    def to_pcm(self):
        raise NotYetImplemented()

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        raise NotYetImplemented()

    #returns this track's number
    #first checking metadata
    #and then making our best-guess from the filename
    #if we come up empty, returns 0
    def track_number(self):
        metadata = self.get_metadata()
        if ((metadata != None) and (metadata.track_number > 0)):
            return metadata.track_number
        else:
            try:
                return int(re.findall(r'\d{2}',self.filename)[0])
            except IndexError:
                return 0

    @classmethod
    def track_name(cls, track_number, track_metadata):
        if (track_metadata != None):
            return (FILENAME_FORMAT % \
                    {"track_number":track_number,
                     "suffix":cls.SUFFIX,
                     "track_name":track_metadata.track_name.replace('/','-'),
                     "album_name":track_metadata.album_name.replace('/','-'),
                     "artist_name":track_metadata.artist_name.replace('/','-')
                     }).encode(FS_ENCODING)
        else:
            return "%(track_number)2.2d.%(suffix)s" % \
                   {"track_number":track_number,
                    "suffix":cls.SUFFIX}

    #takes a list of filenames matching this AudioFile type
    #and adds the proper ReplayGain values to them
    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]

    def __eq__(self, audiofile):
        if (isinstance(audiofile, AudioFile)):
            p1 = self.to_pcm()
            p2 = audiofile.to_pcm()
            try:
                return pcm_cmp(p1,p2)
            finally:
                p1.close()
                p2.close()
        else:
            return False

    def __ne__(self, audiofile):
        return not self.__eq__(audiofile)

    #returns True if all of this AudioFile's required binaries are present
    #checks the __system_binaries__ class for which path to check on
    @classmethod
    def has_binaries(cls, system_binaries):
        import operator

        return reduce(operator.and_,
                      [system_binaries.can_execute(system_binaries[command])
                       for command in cls.BINARIES],
                      True)


class DummyAudioFile(AudioFile):
    def __init__(self, length, metadata):
        self.__length__ = length
        self.__metadata__ = metadata
        
        AudioFile.__init__(self,"")

    def get_metadata(self):
        return self.__metadata__

    def length(self):
        return self.__length__


#######################
#RIFF WAVE
#######################

class WavException(InvalidFile): pass

class WaveAudio(AudioFile):
    SUFFIX = "wav"

    WAVE_HEADER = Con.Struct("wave_header",
                             Con.Bytes("wave_id",4),
                             Con.ULInt32("wave_size"),
                             Con.Bytes("riff_type",4))

    CHUNK_HEADER = Con.Struct("chunk_header",
                              Con.Bytes("chunk_id",4),
                              Con.ULInt32("chunk_length"))
 
    FMT_CHUNK = Con.Struct("fmt_chunk",
                           Con.ULInt16("compression"),
                           Con.ULInt16("channels"),
                           Con.ULInt32("sample_rate"),
                           Con.ULInt32("bytes_per_second"),
                           Con.ULInt16("block_align"),
                           Con.ULInt16("bits_per_sample"))

    
    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        self.__wavtype__ = 0
        self.__channels__ = 0
        self.__samplespersec__ = 0
        self.__bytespersec__ = 0
        self.__blockalign__ = 0
        self.__bitspersample__ = 0
        self.__data_size__ = 0
        
        self.__read_chunks__()

    @classmethod
    def is_type(cls, file):
        header = file.read(12)
        return ((header[0:4] == 'RIFF') and
                (header[8:12] == 'WAVE'))

    def lossless(self):
        return True

    #Returns the PCMReader object for this WAV's data
    def to_pcm(self):
        return WaveReader(file(self.filename,'rb'),
                          sample_rate = self.sample_rate(),
                          channels = self.channels(),
                          bits_per_sample = self.bits_per_sample())

    #Takes a filename and PCMReader containing WAV data
    #builds a WAV from that data and returns a new WaveAudio object
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        f = file(filename,"wb")
        try:
            header = Con.Container()
            header.wave_id = 'RIFF'
            header.riff_type = 'WAVE'
            header.wave_size = 0

            fmt_header = Con.Container()
            fmt_header.chunk_id = 'fmt '
            fmt_header.chunk_length = WaveAudio.FMT_CHUNK.sizeof()

            fmt = Con.Container()
            fmt.compression = 1
            fmt.channels = pcmreader.channels
            fmt.sample_rate = pcmreader.sample_rate
            fmt.bytes_per_second = \
                pcmreader.sample_rate * \
                pcmreader.channels * \
                (pcmreader.bits_per_sample / 8)
            fmt.block_align = \
                pcmreader.channels * \
                (pcmreader.bits_per_sample / 8)
            fmt.bits_per_sample = pcmreader.bits_per_sample

            data_header = Con.Container()
            data_header.chunk_id = 'data'
            data_header.chunk_length = 0

            #write out the basic headers first
            #we'll be back later to clean up the sizes
            f.write(WaveAudio.WAVE_HEADER.build(header))
            f.write(WaveAudio.CHUNK_HEADER.build(fmt_header))
            f.write(WaveAudio.FMT_CHUNK.build(fmt))
            f.write(WaveAudio.CHUNK_HEADER.build(data_header))

            #pcmreader should be little-endian audio
            #we can dump straight into the file
            buffer = pcmreader.read(BUFFER_SIZE)
            while (len(buffer) > 0):
                f.write(buffer)
                data_header.chunk_length += len(buffer)
                buffer = pcmreader.read(BUFFER_SIZE)

            #close up the PCM reader and flush our output
            pcmreader.close()
            f.flush()

            #go back to the beginning the re-write the header
            f.seek(0,0)
            header.wave_size = 4 + \
                WaveAudio.CHUNK_HEADER.sizeof() + \
                WaveAudio.FMT_CHUNK.sizeof() + \
                WaveAudio.CHUNK_HEADER.sizeof() + \
                data_header.chunk_length
            
            f.write(WaveAudio.WAVE_HEADER.build(header))
            f.write(WaveAudio.CHUNK_HEADER.build(fmt_header))
            f.write(WaveAudio.FMT_CHUNK.build(fmt))
            f.write(WaveAudio.CHUNK_HEADER.build(data_header))

        finally:
            f.close()
        
        return WaveAudio(filename)

    def total_samples(self):
        return self.__data_size__ / (self.__bitspersample__ / 8) / \
               self.__channels__

    #returns the rate of samples per second (44100 for CD audio)
    def sample_rate(self):
        return self.__samplespersec__

    #returns the number of channels (2 for CD audio)
    def channels(self):
        return self.__channels__

    #returns the total bits per sample (16 for CD audio)
    def bits_per_sample(self):
        return self.__bitspersample__

    @classmethod
    def track_name(cls, track_number, track_metadata):
        return "track%(track_number)2.2d.cdda.wav" % \
               {"track_number":track_number}

    def __read_chunks__(self):
        wave_file = file(self.filename,"rb")

        __chunklist__ = []

        totalsize = self.__read_wave_header__(wave_file) - 4

        while (totalsize > 0):
            (chunk_format,chunk_size) = self.__read_chunk_header__(wave_file)
            #print chunk_format,chunk_size
            
            __chunklist__.append(chunk_format)
            #Fix odd-sized chunk sizes to be even
            if ((chunk_size & 1) == 1): chunk_size += 1
            
            if (chunk_format == "fmt "):
                self.__read_format_chunk__(wave_file, chunk_size)
            elif (chunk_format == "data"):
                self.__read_data_chunk__(wave_file, chunk_size)
            else:
                wave_file.seek(chunk_size,1)
            totalsize -= (chunk_size + 8)

    def __read_wave_header__(self, wave_file):
        header = WaveAudio.WAVE_HEADER.parse(wave_file.read(12))
        
        if (header.wave_id != "RIFF"):
            raise WavException("not a RIFF WAVE file")
        elif (header.riff_type != "WAVE"):
            raise WavException("not a RIFF WAVE file")
        else:
            return header.wave_size

    def __read_chunk_header__(self, wave_file):
        chunk = WaveAudio.CHUNK_HEADER.parse(wave_file.read(8))
        return (chunk.chunk_id,chunk.chunk_length)

    def __read_format_chunk__(self, wave_file, chunk_size):
        if (chunk_size < 16):
            raise WavException("fmt chunk is too short")

        fmt = WaveAudio.FMT_CHUNK.parse(wave_file.read(chunk_size))
        
        self.__wavtype__ = fmt.compression
        self.__channels__ = fmt.channels
        self.__samplespersec__ = fmt.sample_rate
        self.__bytespersec__ = fmt.bytes_per_second
        self.__blockalign__ = fmt.block_align
        self.__bitspersample__ = fmt.bits_per_sample

        if (self.__wavtype__ != 1):
            raise WavException("no support for compressed WAVE files")

    def __read_data_chunk__(self, wave_file, chunk_size):
        self.__data_size__ = chunk_size
        wave_file.seek(chunk_size,1)


#######################
#AIFF
#######################

class AiffAudio(AudioFile):
    SUFFIX = "aiff"

    def __init__(self, filename):
        import aifc

        AudioFile.__init__(self, filename)

        try:
            f = aifc.open(filename,"r")
            (self.__channels__,
             bytes_per_sample,
             self.__sample_rate__,
             self.__total_samples__,
             self.comptype,
             self.compname) = f.getparams()
            self.__bits_per_sample__ = bytes_per_sample * 8
            f.close()
        except aifc.Error,msg:
            raise InvalidFile(str(msg))

    @classmethod
    def is_type(cls, file):
        header = file.read(12)
        
        return ((header[0:4] == 'FORM') and
                (header[8:12] == 'AIFF'))

    def lossless(self):
        return True

    def bits_per_sample(self):
        return self.__bits_per_sample__

    def channels(self):
        return self.__channels__

    def sample_rate(self):
        return self.__sample_rate__

    def total_samples(self):
        return self.__total_samples__


    def to_pcm(self):
        import aifc

        return FrameReader(aifc.open(self.filename,"r"),
                           self.sample_rate(),
                           self.channels(),
                           self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import aifc

        f = aifc.open(filename,"w")

        f.setparams((pcmreader.channels,
                     pcmreader.bits_per_sample / 8,
                     pcmreader.sample_rate,
                     0,
                     'NONE',
                     'not compressed'))

        transfer_data(pcmreader.read,f.writeframes)
        pcmreader.close()
        f.close()

        return AiffAudio(filename)

    @classmethod
    def track_name(cls, track_number, track_metadata):
        return "track%(track_number)2.2d.cdda.aiff" % \
            {"track_number":track_number}


#######################
#Sun AU
#######################

class AuAudio(AudioFile):
    SUFFIX = "au"

    def __init__(self, filename):
        import sunau

        AudioFile.__init__(self, filename)

        try:
            f = sunau.open(filename,"r")
            (self.__channels__,
             bytes_per_sample,
             self.__sample_rate__,
             self.__total_samples__,
             self.comptype,
             self.compname) = f.getparams()
            self.__bits_per_sample__ = bytes_per_sample * 8
            f.close()
        except sunau.Error,msg:
            raise InvalidFile(str(msg))

    @classmethod
    def is_type(cls, file):
        return file.read(4) == ".snd"

    def lossless(self):
        return True

    def bits_per_sample(self):
        return self.__bits_per_sample__

    def channels(self):
        return self.__channels__

    def sample_rate(self):
        return self.__sample_rate__

    def total_samples(self):
        return self.__total_samples__


    def to_pcm(self):
        import sunau

        return FrameReader(sunau.open(self.filename,"r"),
                           self.sample_rate(),
                           self.channels(),
                           self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import sunau

        f = sunau.open(filename,"w")

        f.setparams((pcmreader.channels,
                     pcmreader.bits_per_sample / 8,
                     pcmreader.sample_rate,
                     0,
                     'NONE',
                     'ULAW'))

        transfer_data(pcmreader.read,f.writeframes)
        pcmreader.close()
        f.close()

        return AuAudio(filename)

    @classmethod
    def track_name(cls, track_number, track_metadata):
        return "track%(track_number)2.2d.cdda.au" % \
               {"track_number":track_number}


#######################
#FLAC
#######################

class FlacException(InvalidFile): pass

class VorbisComment(MetaData,dict):
    VORBIS_COMMENT = Con.Struct("vorbis_comment",
                                Con.PascalString("vendor_string",
                                                 length_field=Con.ULInt32("length")),
                                Con.PrefixedArray(
                                       length_field=Con.ULInt32("length"),
                                       subcon=Con.PascalString("value",
                                                             length_field=Con.ULInt32("length"))))

    ATTRIBUTE_MAP = {'track_name':'TITLE',
                     'track_number':'TRACKNUMBER',
                     'album_name':'ALBUM',
                     'artist_name':'ARTIST',
                     'performer_name':'PERFORMER',
                     'copyright':'COPYRIGHT',
                     'year':'YEAR'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #vorbis_data is a key->[value1,value2,...] dict of the original
    #Vorbis comment data.  keys should be upper case
    def __init__(self, vorbis_data):
        MetaData.__init__(
            self,
            track_name = vorbis_data.get('TITLE',[u''])[0],
            track_number = int(vorbis_data.get('TRACKNUMBER',['0'])[0]),
            album_name = vorbis_data.get('ALBUM',[u''])[0],
            artist_name = vorbis_data.get('ARTIST',[u''])[0],
            performer_name = vorbis_data.get('PERFORMER',[u''])[0],
            copyright = vorbis_data.get('COPYRIGHT',[u''])[0],
            year = vorbis_data.get('YEAR',[u''])[0])
                          
        dict.__init__(self,vorbis_data)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value
        
        if (self.ATTRIBUTE_MAP.has_key(key)):
            if (key != 'track_number'):
                self[self.ATTRIBUTE_MAP[key]] = [value]
            else:
                self[self.ATTRIBUTE_MAP[key]] = [unicode(value)]

    #if a dict pair is updated (e.g. self['TITLE'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        
        if (self.ITEM_MAP.has_key(key)):
            if (key != 'TRACKNUMBER'):
                self.__dict__[self.ITEM_MAP[key]] = value[0]
            else:
                self.__dict__[self.ITEM_MAP[key]] = int(value[0])
        

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,VorbisComment))):
            return metadata
        else:
            values = {}
            for key in cls.ATTRIBUTE_MAP.keys():
                if (getattr(metadata,key) != u""):
                    values[cls.ATTRIBUTE_MAP[key]] = \
                        [unicode(getattr(metadata,key))]

            return VorbisComment(values)

    def __comment_name__(self):
        return u'Vorbis'

    #takes two (key,value) vorbiscomment pairs
    #returns cmp on the weighted set of them
    #(title first, then artist, album, tracknumber, ... , replaygain)
    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {"TITLE":1,
                   "ALBUM":2,
                   "ARTIST":4,
                   "PERFORMER":5,
                   "TRACKNUMBER":3,
                   "COPYRIGHT":7,
                   "YEAR":6,
                   "REPLAYGAIN_ALBUM_GAIN":9,
                   "REPLAYGAIN_ALBUM_PEAK":9,
                   "REPLAYGAIN_TRACK_GAIN":9,
                   "REPLAYGAIN_TRACK_PEAK":9,
                   "REPLAYGAIN_REFERENCE_LOUDNESS":10}
        return cmp((KEY_MAP.get(pair1[0].upper(),8),pair1[0].upper(),pair1[1]),
                   (KEY_MAP.get(pair2[0].upper(),8),pair2[0].upper(),pair2[1]))

    def __comment_pairs__(self):
        pairs = []
        for (key,values) in self.items():
            for value in values:
                pairs.append((key,value))

        pairs.sort(VorbisComment.__by_pair__)
        return pairs

    #returns this VorbisComment as a binary string
    def build(self):
        comment = Con.Container()
        comment.vendor_string = "Python Audio Tools %s" % (VERSION)
        comment.value = []
        for (key,values) in self.items():
            for value in values:
                comment.value.append("%s=%s" % (key,
                                                value.encode('utf-8')))
        return VorbisComment.VORBIS_COMMENT.build(comment)
        

#this is a container for FLAC's PICTURE metadata blocks
class FlacPictureComment:
    def __init__(self, type, mime_type, description,
                 width, height, color_depth, colors_used, data):
        self.type = type
        self.mime_type = mime_type
        self.description = description
        self.width = width
        self.height = height
        self.color_depth = color_depth
        self.colors_used = colors_used
        self.data = data

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
                20:"Publisher/Studio logotype"}.get(self.type,"Other")


    def __repr__(self):
        return "FlacPictureComment(type=%s,mime_type=%s,width=%s,height=%s,...)" % (repr(self.type),repr(self.mime_type),repr(self.width),repr(self.height))

    def __unicode__(self):
        return u"Picture : %s (%d\u00D7%d,'%s')" % \
            (self.type_string(),
             self.width,self.height,self.mime_type)

class FlacComment(VorbisComment):
    def __init__(self, vorbis_comment, picture_comments=()):
        self.picture_comments = picture_comments
        VorbisComment.__init__(self,
                               vorbis_comment)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,FlacComment))):
            return metadata
        elif (isinstance(metadata,VorbisComment)):
            return FlacComment(metadata,())
        else:
            return FlacComment(VorbisComment.converted(metadata),())

    def __unicode__(self):
        if (len(self.picture_comments) == 0):
            return unicode(VorbisComment.__unicode__(self))
        else:
            return u"%s\n\n%s" % \
                (unicode(VorbisComment.__unicode__(self)),
                 "\n".join([unicode(p) for p in self.picture_comments]))


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
                        colors_used=image.color_count,
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
        for picture in metadata.picture_comments:
            picturedata = tempfile.NamedTemporaryFile()
            picturedata.write(picture.data)
            picturedata.flush()
            self.set_picture(picture_filename=picturedata.name,
                             type=picture.type,
                             mime_type=picture.mime_type,
                             description=picture.description,
                             width=picture.width,
                             height=picture.height,
                             depth=picture.color_depth,
                             colors=picture.colors_used)
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

        for comment in VorbisComment.VORBIS_COMMENT.parse(flacdata).value:
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
        flacfile = file(self.filename)

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
                                    Con.Byte('packet_byte'),
                                    Con.String('signature',4),
                                    Con.Byte('major_version'),
                                    Con.Byte('minor_version'),
                                    Con.ULInt16('header_packets'),
                                    Con.String('flac_signature',4),
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
        stream = OggStreamReader(file(self.filename))
        try:
            packets = stream.packets()
            for packet in packets:
                packet = cStringIO.StringIO(packet)
                try:
                    pass
                finally:
                    packet.close()
        finally:
            stream.close()

    def set_metadata(self, metadata):
        pass

    def __read_streaminfo__(self):
        stream = OggStreamReader(file(self.filename))
        try:
            packets = stream.packets()
            header = self.OGGFLAC_STREAMINFO.parse(packets.next())

            self.__samplerate__ = header.samplerate
            self.__channels__ = header.channels + 1
            self.__bitspersample__ = header.bits_per_sample + 1

            #FIXME
            #(might not be valid for PCM-generated OggFLAC
            # we should probably bounce to the end of the file)
            self.__total_samples__ = header.total_samples
            
            del(packets)
        finally:
            stream.close()
        
    @classmethod
    def add_replay_gain(cls, filenames):
        pass

    def __eq__(self, audiofile):
        return AudioFile.__eq__(self, audiofile)

    def cuepoints(self):
        raise ValueError("no cuesheet found")

    def sub_pcm_tracks(self):
        for i in ():
            yield i


#######################
#MP3
#######################

class MP3Exception(InvalidFile): pass
class EndOfID3v2Stream(Exception): pass
class UnsupportedID3v2Version(Exception): pass

class ID3v2Comment(MetaData,dict):
    VALID_FRAME_ID = re.compile(r'[A-Z0-9]{4}')
    FRAME_ID_LENGTH = 4

    ID3v2_HEADER = Con.Struct("id3v2_header",
                              Con.Bytes("file_id",3),
                              Con.Byte("version_major"),
                              Con.Byte("version_minor"),
                              Con.Embed(Con.BitStruct("flags",
                                Con.StrictRepeater(8,
                                                   Con.Flag("flag")))),
                              Con.UBInt32("length"))
  
    FRAME_HEADER = Con.Struct("id3v24_frame",
                              Con.Bytes("frame_id",4),
                              Con.UBInt32("frame_size"),
                              Con.Embed(
            Con.BitStruct("flags",
                          Con.Padding(1),
                          Con.Flag("tag_alter"),
                          Con.Flag("file_alter"),
                          Con.Flag("read_only"),
                          Con.StrictRepeater(5,
                                             Con.Flag("reserved")),
                          Con.Flag("grouping"),
                          Con.Padding(2),
                          Con.Flag("compression"),
                          Con.Flag("encryption"),
                          Con.Flag("unsynchronization"),
                          Con.Flag("data_length"))))

    ATTRIBUTE_MAP = {'track_name':'TIT2',
                     'track_number':'TRCK',
                     'album_name':'TALB',
                     'artist_name':'TPE1',
                     'performer_name':'TPE2',
                     'copyright':'WCOP',
                     'year':'TDRC'}
    
    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))
    
    #takes a filename
    #returns an ID3v2Comment-based object
    @classmethod
    def read_id3v2_comment(cls, filename):        
        f = file(filename)
        
        try:
             if (f.read(3) != 'ID3'): return {}

             frames = {}

             f.seek(0,0)
             header = ID3v2Comment.ID3v2_HEADER.parse_stream(f)
             if (header.version_major == 0x04):
                 comment_class = ID3v2Comment
             elif (header.version_major == 0x03):
                 comment_class = ID3v2_3Comment
             elif (header.version_major == 0x02):
                 comment_class = ID3v2_2Comment
             else:
                 raise UnsupportedID3v2Version()

             while (True):
                 try:
                     (frame_id,frame_data) = \
                         comment_class.read_id3v2_frame(f)
                     frames[frame_id] = frame_data
                 except EndOfID3v2Stream:
                     break

             return comment_class(frames)

        finally:
            f.close()
    
    #takes a stream of ID3v2 data
    #returns a (frame id,frame data) tuple
    #raises EndOfID3v2Stream if we've reached the end of valid frames
    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16',
                      2:'UTF-16BE',
                      3:'UTF-8'}

        frame = cls.FRAME_HEADER.parse_stream(stream)

        if (cls.VALID_FRAME_ID.match(frame.frame_id)):
            if (frame.frame_id.startswith('T')):
                encoding = ord(stream.read(1))
                value = stream.read(cls.__de_syncsafe32__(frame.frame_size) - 1)
                return (frame.frame_id,
                        value.decode(
                            encode_map.get(encoding,
                                           'ISO-8859-1'),
                            'replace').rstrip(unichr(0x00))
                        )
            else:
                return (frame.frame_id,
                        stream.read(cls.__de_syncsafe32__(frame.frame_size)))
        else:
            raise EndOfID3v2Stream()


    #takes a list of ID3v2 syncsafe bytes and returns a single syncsafe int
    @classmethod
    def __de_syncsafe__(cls, bytes):
        #print bytes
        total = 0
        for byte in bytes:
            total = total << 7
            total += (byte & 0x7F)
        return total

    #takes a 28-bit syncsafed int and returns its 32-bit, de-syncsafed value
    @classmethod
    def __de_syncsafe32__(cls, i):
        return (i & 0x7F) + \
               ((i & 0x7F00) >> 1) + \
               ((i & 0x7F0000) >> 2) + \
               ((i & 0x7F000000) >> 3)

    #takes a 32-bit int and returns a 28-bit syncsafed value
    @classmethod
    def __syncsafe32__(cls, i):
        return (i & 0x7F) + \
               ((i & 0x3F80) << 1) + \
               ((i & 0x1FC000) << 2) + \
               ((i & 0xFE00000) << 3)

    #takes a list of (tag_id,tag_value) tuples
    #returns a string of the whole ID3v2.4 tag
    #tag_id should be a raw, 4 character string
    #value should be a unicode string
    @classmethod
    def build_id3v2(cls, taglist):
        tags = []
        for (t_id,t_value) in taglist:
            try:
                t_s = chr(0x00) + t_value.encode('ISO-8859-1')
            except UnicodeEncodeError:
                #t_s = chr(0x02) + t_value.encode('UTF-16-BE') + (chr(0) * 2)
                t_s = chr(0x03) + t_value.encode('UTF-8')

            tag = Con.Container()
            tag.compression = False
            tag.data_length = False
            tag.encryption = False
            tag.file_alter = False
            tag.frame_id = t_id
            tag.frame_size = ID3v2Comment.__syncsafe32__(len(t_s))
            tag.grouping = False
            tag.read_only = False
            tag.tag_alter = True
            tag.unsynchronization = False
            tag.reserved = [0] * 5

            tags.append(cls.FRAME_HEADER.build(tag) + t_s)

        header = Con.Container()
        header.experimental = False
        header.extended_header = False
        header.file_id = 'ID3'
        header.footer = False
        header.length = ID3v2Comment.__syncsafe32__(sum(map(len, tags)))
        header.unsynchronization = False
        header.version_major = 4
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)

    #metadata is a key->value dict of ID3v2 data
    def __init__(self, metadata):
        try:
            tracknum = int(metadata.get("TRCK",
                                        metadata.get("TRK",u"0")))
        except ValueError:
            tracknum = 0
        
        MetaData.__init__(self,
                          track_name=metadata.get("TIT2",
                                                  metadata.get("TT2",u"")),
                          
                          track_number=tracknum,
                          
                          album_name=metadata.get("TALB",
                                                  metadata.get("TAL",u"")),
                          
                          artist_name=metadata.get("TPE1",
                                       metadata.get("TP1",
                                        metadata.get("TOPE",
                                         metadata.get("TCOM",
                                          metadata.get("TOLY",
                                           metadata.get("TEXT",               
                                            metadata.get("TOA",
                                             metadata.get("TCM",u"")))))))),
                                                   
                          performer_name=metadata.get("TPE2",
                                           metadata.get("TPE3",
                                            metadata.get("TPE4",
                                             metadata.get("TP2",
                                              metadata.get("TP3",
                                               metadata.get("TP4",u"")))))),

                          copyright=metadata.get("WCOP",
                                     metadata.get("WCP",u"")),

                          year=metadata.get("TYER",
                                metadata.get("TYE",u""))
                          )
        
        dict.__init__(self,metadata)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (self.ATTRIBUTE_MAP.has_key(key)):
            if (key != 'track_number'):
                self[self.ATTRIBUTE_MAP[key]] = value
            else:
                self[self.ATTRIBUTE_MAP[key]] = unicode(value)

    #if a dict pair is updated (e.g. self['TIT2'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        
        if (self.ITEM_MAP.has_key(key)):
            if (key != 'TRCK'):
                self.__dict__[self.ITEM_MAP[key]] = value
            else:
                self.__dict__[self.ITEM_MAP[key]] = int(value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v2Comment))):
            return metadata

        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            field = getattr(metadata,field)
            if (field != u""):
                tags[key] = unicode(field)
                
        if (tags["TPE1"] == tags["TPE2"]):
            del(tags["TPE2"])

        return ID3v2Comment(tags)

    def build_tag(self):
        return self.build_id3v2(self.items())

    def __comment_name__(self):
        return u'ID3v2.4'

    def __comment_pairs__(self):
        def __weight__(pair):
            if (pair[0] == 'TIT2'):
                return (1,pair[0],pair[1])
            elif (pair[0] in ('TPE1','TPE2','TPE3','TPE4')):
                return (5,pair[0],pair[1])
            elif (pair[0] == 'TALB'):
                return (2,pair[0],pair[1])
            elif (pair[0] == 'TRCK'):
                return (3,pair[0],pair[1])
            elif (pair[0] in ('TOPE','TCOM','TOLY','TEXT')):
                return (4,pair[0],pair[1])
            elif (pair[0].startswith('T')):
                return (6,pair[0],pair[1])
            else:
                return (7,pair[0],pair[1])

        def __by_weight__(item1,item2):
            return cmp(__weight__(item1),
                       __weight__(item2))

        pairs = []

        for (key,value) in sorted(self.items(),__by_weight__):
            if (isinstance(value,unicode)):
                pairs.append(('    ' + key,value))
            else:
                if (len(value) <= 20):
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex'))))
                else:
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex')[0:39].upper()) + u"\u2026"))

        return pairs

    #takes a file stream
    #checks that stream for an ID3v2 comment
    #if found, repositions the stream past it
    #if not, leaves the stream in the current location
    @classmethod
    def skip(cls, file):
        if (file.read(3) == 'ID3'):
            file.seek(0,0)
            #parse the header
            h = ID3v2Comment.ID3v2_HEADER.parse_stream(file)
            #seek to the end of its length
            file.seek(ID3v2Comment.__de_syncsafe32__(h.length),1)
            #skip any null bytes after the ID3v2 tag
            c = file.read(1)
            while (c == '\x00'):
                c = file.read(1)
            file.seek(-1,1)
        else:
            try:
                file.seek(-3,1)
            except IOError:
                pass

class ID3v2_3Comment(ID3v2Comment):
    FRAME_HEADER = Con.Struct("id3v23_frame",
                              Con.Bytes("frame_id",4),
                              Con.UBInt32("frame_size"),
                              Con.Embed(
            Con.BitStruct("flags",
                          Con.Flag("tag_alter"),
                          Con.Flag("file_alter"),
                          Con.Flag("read_only"),
                          Con.Padding(5),
                          Con.Flag("compression"),
                          Con.Flag("encryption"),
                          Con.Flag("grouping"),
                          Con.Padding(5))))

    ATTRIBUTE_MAP = {'track_name':'TIT2',
                     'track_number':'TRCK',
                     'album_name':'TALB',
                     'artist_name':'TPE1',
                     'performer_name':'TPE2',
                     'copyright':'WCOP',
                     'year':'TDRC'}
    
    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #takes a stream of ID3v2 data
    #returns a (frame id,frame data) tuple
    #raises EndOfID3v2Stream if we've reached the end of valid frames
    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16'}

        frame = cls.FRAME_HEADER.parse_stream(stream)

        if (cls.VALID_FRAME_ID.match(frame.frame_id)):
            if (frame.frame_id.startswith('T')):
                encoding = ord(stream.read(1))
                value = stream.read(frame.frame_size - 1)

                return (frame.frame_id,
                        value.decode(
                        encode_map.get(encoding,
                                       'ISO-8859-1'),
                        'replace').rstrip(unichr(0x00))
                        )
            else:
                return (frame.frame_id,
                        stream.read(frame.frame_size))
        else:
            raise EndOfID3v2Stream()

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v2_3Comment))):
            return metadata

        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            field = getattr(metadata,field)
            if (field != u""):
                tags[key] = unicode(field)

        if (tags["TPE1"] == tags["TPE2"]):
            del(tags["TPE2"])

        return ID3v2_3Comment(tags)

    def __comment_name__(self):
        return u'ID3v2.3'

    @classmethod
    def build_id3v2(cls, taglist):
        tags = []

        for (t_id,t_value) in taglist:
            try:
                t_s = chr(0x00) + t_value.encode('ISO-8859-1')
            except UnicodeEncodeError:
                t_s = chr(0x01) + t_value.encode('UTF-16')

            tag = Con.Container()
            tag.tag_alter = False
            tag.file_alter = False
            tag.read_only = False
            tag.compression = False
            tag.encryption = False
            tag.grouping = False
            tag.frame_id = t_id
            tag.frame_size = len(t_s)

            tags.append(cls.FRAME_HEADER.build(tag) + t_s)
        
        header = Con.Container()
        header.experimental = False
        header.extended_header = False
        header.file_id = 'ID3'
        header.footer = False
        header.length = ID3v2Comment.__syncsafe32__(sum(map(len, tags)))
        header.unsynchronization = False
        header.version_major = 3
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)

class ID3v2_2Comment(ID3v2Comment):
    VALID_FRAME_ID = re.compile(r'[A-Z0-9]{3}')
    FRAME_ID_LENGTH = 3

    FRAME_HEADER = Con.Struct("id3v22_frame",
                              Con.Bytes("frame_id",3),
                              Con.Embed(Con.BitStruct("size",
            Con.Bits("frame_size",24))))

    ATTRIBUTE_MAP = {'track_name':'TT2',
                     'track_number':'TRK',
                     'album_name':'TAL',
                     'artist_name':'TP1',
                     'performer_name':'TP2',
                     'copyright':'WCP',
                     'year':'TYE'}
    
    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16'}

        frame = cls.FRAME_HEADER.parse_stream(stream)
        if (cls.VALID_FRAME_ID.match(frame.frame_id)):
            if (frame.frame_id.startswith('T')):
                encoding = ord(stream.read(1))
                value = stream.read(frame.frame_size - 1)
                return (frame.frame_id,
                        value.decode(encode_map.get(encoding,'ISO-8859-1'),
                                     'replace').rstrip(unichr(0x00)))
            else:
                return (frame.frame_id,
                        stream.read(frame.frame_size))
        else:
            raise EndOfID3v2Stream()

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v2_2Comment))):
            return metadata

        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            field = getattr(metadata,field)
            if (field != u""):
                tags[key] = unicode(field)

        if (tags["TP1"] == tags["TP2"]):
            del(tags["TP2"])

        return ID3v2_2Comment(tags)

    def __comment_name__(self):
        return u'ID3v2.2'

    def __comment_pairs__(self):
        def __weight__(pair):
            if (pair[0] == 'TT2'):
                return (1,pair[0],pair[1])
            elif (pair[0] in ('TP1','TP2','TP3','TP4')):
                return (5,pair[0],pair[1])
            elif (pair[0] == 'TAL'):
                return (2,pair[0],pair[1])
            elif (pair[0] == 'TRK'):
                return (3,pair[0],pair[1])
            elif (pair[0] in ('TOA','TCM')):
                return (4,pair[0],pair[1])
            elif (pair[0].startswith('T')):
                return (6,pair[0],pair[1])
            else:
                return (7,pair[0],pair[1])

        def __by_weight__(item1,item2):
            return cmp(__weight__(item1),
                       __weight__(item2))

        pairs = []

        for (key,value) in sorted(self.items(),__by_weight__):
            if (isinstance(value,unicode)):
                pairs.append(('    ' + key,value))
            else:
                if (len(value) <= 20):
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex'))))
                else:
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex')[0:39].upper()) + u"\u2026"))

        return pairs


    @classmethod
    def build_id3v2(cls, taglist):
        tags = []

        for (t_id,t_value) in taglist:
            try:
                t_s = chr(0x00) + t_value.encode('ISO-8859-1')
            except UnicodeEncodeError:
                t_s = chr(0x01) + t_value.encode('UTF-16')

            tag = Con.Container()
            tag.frame_id = t_id
            tag.frame_size = len(t_s)

            tags.append(cls.FRAME_HEADER.build(tag) + t_s)
        
        header = Con.Container()
        header.experimental = False
        header.extended_header = False
        header.file_id = 'ID3'
        header.footer = False
        header.length = ID3v2Comment.__syncsafe32__(sum(map(len, tags)))
        header.unsynchronization = False
        header.version_major = 3
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)


class ID3v1Comment(MetaData,list):
    ID3v1 = Con.Struct("id3v1",
      Con.String("identifier",3),
      Con.String("song_title",30),
      Con.String("artist",30),
      Con.String("album",30),
      Con.String("year",4),
      Con.String("comment",28),
      Con.Padding(1),
      Con.Byte("track_number"),
      Con.Byte("genre"))
  
    ID3v1_NO_TRACKNUMBER = Con.Struct("id3v1_notracknumber",
      Con.String("identifier",3),
      Con.String("song_title",30),
      Con.String("artist",30),
      Con.String("album",30),
      Con.String("year",4),
      Con.String("comment",30),
      Con.Byte("genre"))

    ATTRIBUTES = ['track_name',
                  'artist_name',
                  'album_name',
                  'year',
                  'comment',
                  'track_number']
    
    #takes an open mp3 file object
    #returns a (song title, artist, album, year, comment, track number) tuple
    #if no ID3v1 tag is present, returns a tuple with those fields blank
    #all text is in unicode
    #if track number is -1, the id3v1 comment could not be found
    @classmethod
    def read_id3v1_comment(cls, mp3filename):
        mp3file = file(mp3filename,"rb")
        try:
            mp3file.seek(-128,2)
            try:
                id3v1 = ID3v1Comment.ID3v1.parse(mp3file.read())
            except Con.adapters.PaddingError:
                mp3file.seek(-128,2)
                id3v1 = ID3v1Comment.ID3v1_NO_TRACKNUMBER.parse(mp3file.read())
                id3v1.track_number = 0

            if (id3v1.identifier == 'TAG'):
                field_list = (id3v1.song_title,
                              id3v1.artist,
                              id3v1.album,
                              id3v1.year,
                              id3v1.comment)
                
                return tuple(map(lambda t:
                                   t.rstrip('\x00').decode('ascii','replace'),
                                 field_list) + [id3v1.track_number])
            else:
                return tuple([u""] * 5 + [-1])
        finally:
            mp3file.close()


    #takes several unicode strings (except for track_number, an int)
    #pads them with nulls and returns a complete ID3v1 tag
    @classmethod
    def build_id3v1(cls, song_title, artist, album, year, comment,
                    track_number):
        def __s_pad__(s,length):
            if (len(s) < length):
                return s + chr(0) * (length - len(s))
            else:
                return s[0:length]

        c = Con.Container()
        c.identifier = 'TAG'
        c.song_title = __s_pad__(song_title.encode('ascii','replace'),30)
        c.artist = __s_pad__(artist.encode('ascii','replace'),30)
        c.album = __s_pad__(album.encode('ascii','replace'),30)
        c.year = __s_pad__(year.encode('ascii','replace'),4)
        c.comment = __s_pad__(comment.encode('ascii','replace'),28)
        c.track_number = int(track_number)
        c.genre = 0

        return ID3v1Comment.ID3v1.build(c)

    #metadata is the title,artist,album,year,comment,tracknum tuple returned by
    #read_id3v1_comment
    def __init__(self, metadata):
        MetaData.__init__(self,
                          track_name=metadata[0],
                          track_number=metadata[5],
                          album_name=metadata[2],
                          artist_name=metadata[1],
                          performer_name=u"",
                          copyright=u"",
                          year=unicode(metadata[3]))
        list.__init__(self, metadata)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding list item
    def __setattr__(self, key, value):
        self.__dict__[key] = value
        
        if (key in self.ATTRIBUTES):
            if (key != 'track_number'):
                self[self.ATTRIBUTES.index(key)] = value
            else:
                self[self.ATTRIBUTES.index(key)] = int(value)

    #if a list item is updated (e.g. self[1])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)
        
        if (key < len(self.ATTRIBUTES)):
            if (key != 5):
                self.__dict__[self.ATTRIBUTES[key]] = value
            else:
                self.__dict__[self.ATTRIBUTES[key]] = int(value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v1Comment))):
            return metadata

        return ID3v1Comment((metadata.track_name,
                             metadata.artist_name,
                             metadata.album_name,
                             metadata.year,
                             u"",
                             int(metadata.track_number)))

    def __comment_name__(self):
        return u'ID3v1'

    def __comment_pairs__(self):
        return zip(('Title','Artist','Album','Year','Comment','Tracknum'),
                   self)

    def build_tag(self):
        return self.build_id3v1(self.track_name,
                                self.artist_name,
                                self.album_name,
                                self.year,
                                u"",
                                self.track_number)


class ID3CommentPair(MetaData):
    #id3v2 and id3v1 are ID3v2Comment and ID3v1Comment objects or None
    #values in ID3v2 take precendence over ID3v1, if present
    def __init__(self, id3v2_comment, id3v1_comment):
        self.__dict__['id3v2'] = id3v2_comment
        self.__dict__['id3v1'] = id3v1_comment

        if (self.id3v2 != None):
            base_comment = self.id3v2
        elif (self.id3v1 != None):
            base_comment = self.id3v1
        else:
            raise ValueError("id3v2 and id3v1 cannot both be blank")

        MetaData.__init__(
            self,
            track_name=base_comment.track_name,
            track_number=base_comment.track_number,
            album_name=base_comment.album_name,
            artist_name=base_comment.artist_name,
            performer_name=base_comment.performer_name,
            copyright=base_comment.copyright,
            year=base_comment.year)

    def __setattr__(self, key, value):
        if (self.id3v2 != None):
            setattr(self.id3v2,key,value)
        if (self.id3v1 != None):
            setattr(self.id3v1,key,value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3CommentPair))):
            return metadata

        return ID3CommentPair(
            ID3v2_3Comment.converted(metadata),
            ID3v1Comment.converted(metadata))
            

    def __unicode__(self):
        if ((self.id3v2 != None) and (self.id3v1 != None)):
            #both comments present
            return unicode(self.id3v2) + \
                   (os.linesep * 2) + \
                   unicode(self.id3v1)
        elif (self.id3v2 != None):
            #only ID3v2
            return unicode(self.id3v2)
        elif (self.id3v1 != None):
            #only ID3v1
            return unicode(self.id3v1)
        else:
            return u''


class MP3Audio(AudioFile):
    SUFFIX = "mp3"
    DEFAULT_COMPRESSION = "standard"
    COMPRESSION_MODES = ("medium","standard","extreme","insane")
    BINARIES = ("lame",)
    
    #MPEG1, Layer 1
    #MPEG1, Layer 2,
    #MPEG1, Layer 3,
    #MPEG2, Layer 1,
    #MPEG2, Layer 2,
    #MPEG2, Layer 3
    MP3_BITRATE = ((None,None,None,None,None,None),
                   (32,32,32,32,8,8),
                   (64,48,40,48,16,16),
                   (96,56,48,56,24,24),
                   (128,64,56,64,32,32),
                   (160,80,64,80,40,40),
                   (192,96,80,96,48,48),
                   (224,112,96,112,56,56),
                   (256,128,112,128,64,64),
                   (288,160,128,144,80,80),
                   (320,192,160,160,96,96),
                   (352,224,192,176,112,112),
                   (384,256,224,192,128,128),
                   (416,320,256,224,144,144),
                   (448,384,320,256,160,160))

    #MPEG1, MPEG2, MPEG2.5
    MP3_SAMPLERATE = ((44100,22050,11025),
                      (48000,24000,12000),
                      (32000,16000,8000))

    MP3_FRAME_HEADER = Con.BitStruct("mp3_header",
                                  Con.Bits("sync",11),
                                  Con.Bits("mpeg_version",2),
                                  Con.Bits("layer",2),
                                  Con.Bits("protection",1),
                                  Con.Bits("bitrate",4),
                                  Con.Bits("sampling_rate",2),
                                  Con.Bits("padding",1),
                                  Con.Bits("private",1),
                                  Con.Bits("channel",2),
                                  Con.Bits("mode_extension",2),
                                  Con.Bits("copyright",1),
                                  Con.Bits("original",1),
                                  Con.Bits("emphasis",2))
  
    XING_HEADER = Con.Struct("xing_header",
                             Con.Bytes("header_id",4),
                             Con.Bytes("flags",4),
                             Con.UBInt32("num_frames"),
                             Con.UBInt32("bytes"),
                             Con.StrictRepeater(100,Con.Byte("toc_entries")),
                             Con.UBInt32("quality"))
    
    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        mp3file = file(filename,"rb")
        try:
            MP3Audio.__find_next_mp3_frame__(mp3file)
            fr = MP3Audio.MP3_FRAME_HEADER.parse(mp3file.read(4))
            self.__samplerate__ = MP3Audio.__get_mp3_frame_sample_rate__(fr)
            self.__channels__ = MP3Audio.__get_mp3_frame_channels__(fr)
            self.__framelength__ = self.__length__()
        finally:
            mp3file.close()
            
    @classmethod
    def is_type(cls, file):
        ID3v2Comment.skip(file)
        
        try:
            frame = cls.MP3_FRAME_HEADER.parse_stream(file)
            return ((frame.sync == 0x07FF) and
                    (frame.mpeg_version in (0x03,0x02,0x00)) and
                    (frame.layer in (0x01,0x03)))
        except:
            return False

    def lossless(self):
        return False
            
    def to_pcm(self):
        sub = subprocess.Popen([BIN['lame'],"--decode","-t","--quiet",
                                self.filename,"-"],
                               stdout=subprocess.PIPE)
        return PCMReader(sub.stdout,
                         sample_rate=self.sample_rate(),
                         channels=self.channels(),
                         bits_per_sample=16,
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="standard"):
        import decimal
        
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.channels > 2):
            raise InvalidFormat('mp3 only supports up to 2 channels')
        elif (pcmreader.channels > 1):
            mode = "j"
        else:
            mode = "m"
        
        sub = subprocess.Popen([BIN['lame'],"--quiet",
                                "-r","-x",
                                "-s",str(
            decimal.Decimal(pcmreader.sample_rate) / 1000),
                                "--bitwidth",str(pcmreader.bits_per_sample),
                                "-m",mode,
                                "--preset",compression,
                                "-",
                                filename],
                               stdin=subprocess.PIPE)

        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()
        sub.wait()
        
        return MP3Audio(filename)

    def bits_per_sample(self):
        return 16

    def channels(self):
        return self.__channels__

    def sample_rate(self):
        return self.__samplerate__

    def get_metadata(self):
        f = file(self.filename)
        try:
            if (f.read(3) != "ID3"):      #no ID3v2 tag, try ID3v1
                id3v1 = ID3v1Comment.read_id3v1_comment(self.filename)
                if (id3v1[-1] == -1):     #no ID3v1 either
                    return None
                else:
                    return ID3v1Comment(id3v1)
            else:
                id3v2 = ID3v2Comment.read_id3v2_comment(self.filename)

                id3v1 = ID3v1Comment.read_id3v1_comment(self.filename)
                if (id3v1[-1] == -1):      #only ID3v2, no ID3v1
                    return id3v2
                else:                      #both ID3v2 and ID3v1
                    return ID3CommentPair(
                        id3v2,
                        ID3v1Comment(id3v1))
        finally:
            f.close()

    def set_metadata(self, metadata):
        metadata = ID3CommentPair.converted(metadata)
        
        if (metadata == None): return

        #get the original MP3 data
        f = file(self.filename,"rb")
        MP3Audio.__find_next_mp3_frame__(f)
        data_start = f.tell()
        MP3Audio.__find_last_mp3_frame__(f)
        data_end = f.tell()
        f.seek(data_start,0)
        mp3_data = f.read(data_end - data_start)
        f.close()

        id3v2 = metadata.id3v2.build_tag()
        id3v1 = metadata.id3v1.build_tag()

        #write id3v2 + data + id3v1 to file
        f = file(self.filename,"wb")
        f.write(id3v2)
        f.write(mp3_data)
        f.write(id3v1)
        f.close()

    #places mp3file at the position of the next MP3 frame's start
    @classmethod
    def __find_next_mp3_frame__(cls, mp3file):
        #if we're starting at an ID3v2 header, skip it and save a bunch of time
        ID3v2Comment.skip(mp3file)

        #then find the next mp3 frame
        (b1,b2) = mp3file.read(2)
        while ((b1 != '\xff') or
               ((ord(b2) & 0xE0) != 0xE0)):
            (b1,b2) = mp3file.read(2)
        mp3file.seek(-2,1)
    
    #places mp3file at the position of the last MP3 frame's end
    #(either the last byte in the file or just before the ID3v1 tag)
    @classmethod
    def __find_last_mp3_frame__(cls, mp3file):
        mp3file.seek(-128,2)
        if (mp3file.read(3) == 'TAG'):
            mp3file.seek(-128,2)
            return
        else:
            mp3file.seek(0,2)
        return
            
    #header is a Construct parsed from 4 bytes sent to MP3_FRAME_HEADER
    #returns the total length of the frame, including the header
    #(subtract 4 when doing a seek or read to the next one)
    @classmethod
    def __mp3_frame_length__(cls, header):
        layer = 4 - header.layer  #layer 1, 2 or 3

        bit_rate = MP3Audio.__get_mp3_frame_bitrate__(header)
        if (bit_rate == None): raise MP3Exception("invalid bit rate")
        
        sample_rate = MP3Audio.__get_mp3_frame_sample_rate__(header)

        #print layer,sample_rate,bit_rate
        if (layer == 1):
            return (12 * (bit_rate * 1000) / sample_rate + header.padding) * 4
        else:
            return 144 * (bit_rate * 1000) / sample_rate + header.padding


    #takes a parsed MP3_FRAME_HEADER
    #returns the mp3's sample rate based on that information
    #(typically 44100)
    @classmethod
    def __get_mp3_frame_sample_rate__(cls, frame):
        try:
            if (frame.mpeg_version == 0x00):   #MPEG 2.5
                return MP3Audio.MP3_SAMPLERATE[frame.sampling_rate][2]
            elif (frame.mpeg_version == 0x02): #MPEG 2
                return MP3Audio.MP3_SAMPLERATE[frame.sampling_rate][1]
            else:                              #MPEG 1
                return MP3Audio.MP3_SAMPLERATE[frame.sampling_rate][0]
        except IndexError:
            raise MP3Exception("invalid sampling rate")

    @classmethod
    def __get_mp3_frame_channels__(cls, frame):
        if (frame.channel == 0x03):
            return 1
        else:
            return 2

    @classmethod
    def __get_mp3_frame_bitrate__(cls, frame):
        layer = 4 - frame.layer  #layer 1, 2 or 3

        try:
            if (frame.mpeg_version == 0x00):   #MPEG 2.5
                return MP3Audio.MP3_BITRATE[frame.bitrate][layer + 2]
            elif (frame.mpeg_version == 0x02): #MPEG 2
                return MP3Audio.MP3_BITRATE[frame.bitrate][layer + 2]
            elif (frame.mpeg_version == 0x03): #MPEG 1
                return MP3Audio.MP3_BITRATE[frame.bitrate][layer - 1]
            else:
                return 0
        except IndexError:
            raise MP3Exception("invalid bit rate")

    def length(self):
        #calculate length at create-time so that we can
        #throw MP3Exception as soon as possible
        return self.__framelength__

    #returns the length of this file in CD frame
    #raises MP3Exception if any portion of the frame is invalid
    def __length__(self):
        mp3file = file(self.filename,"rb")
    
        try:
            MP3Audio.__find_next_mp3_frame__(mp3file)

            start_position = mp3file.tell()

            fr = MP3Audio.MP3_FRAME_HEADER.parse(mp3file.read(4))

            first_frame = mp3file.read(MP3Audio.__mp3_frame_length__(fr) - 4)

            sample_rate = MP3Audio.__get_mp3_frame_sample_rate__(fr)

            if (fr.mpeg_version == 0x00):   #MPEG 2.5
                version = 3
            elif (fr.mpeg_version == 0x02): #MPEG 2
                version = 3
            else:                           #MPEG 1
                version = 0

            try:
                if (fr.layer == 0x03):   #layer 1
                    frames_per_sample = 384
                    bit_rate = MP3Audio.MP3_BITRATE[fr.bitrate][version]
                elif (fr.layer == 0x02): #layer 2
                    frames_per_sample = 1152
                    bit_rate = MP3Audio.MP3_BITRATE[fr.bitrate][version + 1]
                elif (fr.layer == 0x01): #layer 3
                    frames_per_sample = 1152
                    bit_rate = MP3Audio.MP3_BITRATE[fr.bitrate][version + 2]
                else:
                    raise MP3Exception("unsupported MPEG layer")
            except IndexError:
                raise MP3Exception("invalid bit rate")

            if ('Xing' in first_frame):
                #the first frame has a Xing header,
                #use that to calculate the mp3's length
                xing_header = MP3Audio.XING_HEADER.parse(
                    first_frame[first_frame.index('Xing'):])

                return (xing_header.num_frames * frames_per_sample * 75 / sample_rate)
            else:
                #no Xing header,
                #assume a constant bitrate file
                mp3file.seek(-128,2)
                if (mp3file.read(3) == "TAG"):
                    end_position = mp3file.tell() - 3
                else:
                    mp3file.seek(0,2)
                    end_position = mp3file.tell()

                return (end_position - start_position) * 75 * 8 / (bit_rate * 1000)
        finally:
            mp3file.close()

    def total_samples(self):
        return self.length() * self.sample_rate()

#######################
#MP2 AUDIO
#######################

class MP2Audio(MP3Audio):
    SUFFIX = "mp2"
    DEFAULT_COMPRESSION = str(192)
    COMPRESSION_MODES = map(str,(32, 48, 56, 64, 80, 96, 112,
                                 128,160,192,224,256,320,384))
    BINARIES = ("lame","twolame")

    @classmethod
    def is_type(cls, file):
        ID3v2Comment.skip(file)
        
        try:
            frame = cls.MP3_FRAME_HEADER.parse_stream(file)

            return ((frame.sync == 0x07FF) and
                    (frame.mpeg_version in (0x03,0x02,0x00)) and
                    (frame.layer == 0x02))
        except:
            return False

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="192"):
        import decimal
        
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.channels > 2):
            raise InvalidFormat('mp2 only supports up to 2 channels')

        if (pcmreader.sample_rate not in (44100,48000,32000)):
            raise InvalidFormat('mp2 only supports sample rates 32000,48000 and 44100')
        
        sub = subprocess.Popen([BIN['twolame'],"--quiet",
                                "-r",
                                "-s",str(pcmreader.sample_rate),
                                "--samplesize",str(pcmreader.bits_per_sample),
                                "-N",str(pcmreader.channels),
                                "-m","a",
                                "-b",compression,
                                "-",
                                filename],
                               stdin=subprocess.PIPE)

        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()
        sub.wait()
        
        return MP2Audio(filename)


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
                     'artist_name':'Composer',
                     'performer_name':'Artist',
                     'copyright':'Copyright',
                     'year':'Year'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    def __init__(self, tag_dict, tag_length=None):
        MetaData.__init__(self,
                          track_name=tag_dict.get('Title',u''),
                          track_number=int(tag_dict.get('Track',u'0')),
                          album_name=tag_dict.get('Album',u''),
                          artist_name=tag_dict.get('Composer',u''),
                          performer_name=tag_dict.get('Artist',u''),
                          copyright=tag_dict.get('Copyright',u''),
                          year=tag_dict.get('Year',u'')
                          )
        dict.__init__(self, tag_dict)
        self.tag_length = tag_length

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value
        
        if (self.ATTRIBUTE_MAP.has_key(key)):
            if (key != 'track_number'):
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
            for (key,field) in item_map.items():
                field = unicode(getattr(metadata,field))
                if (field != u''):
                    tags[key] = field
                
            return ApeTag(tags)

    def __comment_name__(self):
        return u'APEv2'

    #takes two (key,value) apetag pairs
    #returns cmp on the weighted set of them
    #(title first, then artist, album, tracknumber)
    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {"Title":1,
                   "Album":2,
                   "Track":3,
                   "Composer":4,
                   "Artist":5,
                   "Copyright":7,
                   "Year":6}
        
        return cmp((KEY_MAP.get(pair1[0],8),pair1[0],pair1[1]),
                   (KEY_MAP.get(pair2[0],8),pair2[0],pair2[1]))

    def __comment_pairs__(self):
        return sorted(self.items(),ApeTag.__by_pair__)
        

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
            apev2tag[tag.key] = tag.value.rstrip("\0").decode('utf-8',
                                                              'replace')

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
            value = value.encode('utf-8')
            tag = Con.Container()
            tag.length = len(value)
            tag.key = key
            tag.value = value

            tag.undefined1 = tag.undefined2 = tag.undefined3 = 0
            tag.read_only = False
            tag.encoding = 0
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
        f = file(self.filename,'r')
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
            f = file(self.filename,"r")
            untagged_data = f.read()[0:-current_metadata.tag_length]
            f.close()
            f = file(self.filename,"w")
            f.write(untagged_data)
            f.write(apetag.ape_tag_data())
            f.close()
        else:                           #no existing tags
            f = file(self.filename,"a")
            f.write(apetag.ape_tag_data())
            f.close()


class ApeAudio(ApeTaggedAudio,AudioFile):
    SUFFIX = "ape"
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

    def bits_per_sample(self):
        return self.__bitspersample__

    def channels(self):
        return self.__channels__

    def total_samples(self):
        return self.__totalsamples__

    def sample_rate(self):
        return self.__samplespersec__
    

    @classmethod
    def __ape_info__(cls, filename):
        f = file(filename,'r')
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
        devnull = file(os.devnull,"wb")
        sub = subprocess.Popen([BIN['mac'],
                                self.filename,
                                f.name,
                                '-d'],
                               stdout=devnull,
                               stderr=devnull)
        sub.wait()
        devnull.close()
        f.seek(0,0)
        return TempWaveReader(f)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import tempfile

        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        w = WaveAudio.from_pcm(f.name, pcmreader)
        devnull = file(os.devnull,"wb")
        sub = subprocess.Popen([BIN['mac'],
                                w.filename,
                                filename,
                                "-c%s" % (compression)],
                               stdout=devnull,
                               stderr=devnull)
        sub.wait()
        devnull.close()
        del(w)
        f.close()
        return ApeAudio(filename)


#######################
#Vorbis File
#######################

class VorbisAudio(AudioFile):
    SUFFIX = "ogg"
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
        f = OggStreamReader(file(self.filename,"r"))
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
                raise InvalidFile('first packet is not vorbis')
            
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

    def total_samples(self):
        pcm_samples = 0
        f = file(self.filename,"r")
        try:
            while (True):
                try:
                    page = OggStreamReader.OGGS.parse_stream(f)
                    pcm_samples = page.granule_position
                    f.seek(sum(page.segment_lengths),1)
                except Con.core.FieldError:
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

        return PCMReader(sub.stdout,
                         sample_rate = self.__sample_rate__,
                         channels = self.__channels__,
                         bits_per_sample = self.bits_per_sample(),
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        sub = subprocess.Popen([BIN['oggenc'],'-Q',
                                '-r',
                                '-B',str(pcmreader.bits_per_sample),
                                '-C',str(pcmreader.channels),
                                '-R',str(pcmreader.sample_rate),
                                '--raw-endianness',str(0),
                                '-q',compression,
                                '-o',filename,'-'],
                               stdin=subprocess.PIPE)

        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()
        sub.wait()

        return VorbisAudio(filename)

    def set_metadata(self, metadata):
        metadata = VorbisComment.converted(metadata)
        
        if (metadata == None): return

        sub = subprocess.Popen([BIN['vorbiscomment'],
                                "-R","-w",self.filename],
                               stdin=subprocess.PIPE)
        
        for (tag,values) in metadata.items():
            for value in values:
                print >>sub.stdin,"%(tag)s=%(value)s" % \
                      {"tag":tag,"value":unicode(value).encode('utf-8')}
        sub.stdin.close()
        sub.wait()

        self.__read_metadata__()

    def get_metadata(self):
        data = {}
        for pair in self.comment.value:
            (key,value) = pair.split('=',1)
            data.setdefault(key,[]).append(value.decode('utf-8'))

        return VorbisComment(data)

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]     

        if ((len(track_names) > 0) and
            BIN.can_execute(BIN['vorbisgain'])):
            devnull = file(os.devnull,'a')

            sub = subprocess.Popen([BIN['vorbisgain'],
                                    '-q','-a'] + track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()
        

#######################
#Speex File
#######################

class SpeexAudio(VorbisAudio):
    SUFFIX = "spx"
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple([str(i) for i in range(0,11)])
    BINARIES = ("speexenc","speexdec")

    SPEEX_HEADER = Con.Struct('speex_header',
                              Con.String('speex_string',8),
                              Con.String('speex_version',20),
                              Con.ULInt32('speex_version_id'),
                              Con.ULInt32('header_size'),
                              Con.ULInt32('sampling_rate'),
                              Con.ULInt32('mode'),
                              Con.ULInt32('mode_bitstream_version'),
                              Con.ULInt32('channels'),
                              Con.ULInt32('bitrate'),
                              Con.ULInt32('frame_size'),
                              Con.ULInt32('vbr'),
                              Con.ULInt32('frame_per_packet'),
                              Con.ULInt32('extra_headers'),
                              Con.ULInt32('reserved1'),
                              Con.ULInt32('reserved2'))

    def __init__(self, filename):
        AudioFile.__init__(self, filename)
        self.__read_metadata__()

    @classmethod
    def is_type(cls, file):
        header = file.read(0x23)
        
        return (header.startswith('OggS') and
                header[0x1C:0x23] == 'Speex  ')

    def __read_metadata__(self):
        f = OggStreamReader(file(self.filename,"r"))
        packets = f.packets()
        try:
            #first read the Header packet
            header = SpeexAudio.SPEEX_HEADER.parse(packets.next())

            self.__sample_rate__ = header.sampling_rate
            self.__channels__ = header.channels

            #the read the Comment packet
            comment_packet = packets.next()

            self.comment = VorbisComment.VORBIS_COMMENT.parse(
                comment_packet)
        finally:
            del(packets); f.close(); del(f)

    def to_pcm(self):
        devnull = file(os.devnull,'a')
        sub = subprocess.Popen([BIN['speexdec'],self.filename,'-'],
                               stdout=subprocess.PIPE,
                               stderr=devnull)
        return PCMReader(sub.stdout,
                         sample_rate=self.sample_rate(),
                         channels=self.channels(),
                         bits_per_sample=self.bits_per_sample(),
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.bits_per_sample not in (8,16)):
            raise InvalidFormat('speex only supports 8 or 16-bit samples')
        else:
            BITS_PER_SAMPLE = {8:['--8bit'],
                               16:['--16bit']}[pcmreader.bits_per_sample]

        if (pcmreader.channels > 2):
            raise InvalidFormat('speex only supports up to 2 channels')
        else:
            CHANNELS = {1:[],2:['--stereo']}[pcmreader.channels]

        devnull = file(os.devnull,"a")

        sub = subprocess.Popen([BIN['speexenc'],
                                '--quality',str(compression),
                                '--rate',str(pcmreader.sample_rate),
                                '--le'] + \
                               BITS_PER_SAMPLE + \
                               CHANNELS + \
                               ['-',filename],
                               stdin=subprocess.PIPE,
                               stderr=devnull)

        transfer_data(pcmreader.read,sub.stdin.write)
        pcmreader.close()
        sub.stdin.close()
        sub.wait()
        devnull.close()

        return SpeexAudio(filename)

    def set_metadata(self, metadata):
        comment = VorbisComment.converted(metadata)
        
        if (comment == None): return

        reader = OggStreamReader(file(self.filename,'r'))
        new_file = cStringIO.StringIO()
        writer = OggStreamWriter(new_file)

        pages = reader.pages()

        #transfer our old header
        (header_page,header_data) = pages.next()
        writer.write_page(header_page,header_data)

        #skip the existing comment packet
        (page,data) = pages.next()
        while (page.segment_lengths[-1] == 255):
            (page,data) = pages.next()

        #write the pages for our new comment packet
        comment_pages = OggStreamWriter.build_pages(
            0,
            header_page.bitstream_serial_number,
            header_page.page_sequence_number + 1,
            comment.build())

        for (page,data) in comment_pages:
            writer.write_page(page,data)

        #write the rest of the pages, re-sequenced and re-checksummed
        sequence_number = comment_pages[-1][0].page_sequence_number + 1
        for (i,(page,data)) in enumerate(pages):
            page.page_sequence_number = i + sequence_number
            page.checksum = OggStreamReader.calculate_ogg_checksum(page,data)
            writer.write_page(page,data)

        reader.close()

        #re-write the file with our new data in "new_file"
        f = file(self.filename,"w")
        f.write(new_file.getvalue())
        f.close()
        writer.close()
        


class OggStreamReader:
    OGGS = Con.Struct(
        "oggs",
        Con.String("magic_number",4),
        Con.Byte("version"),
        Con.Byte("header_type"),
        Con.ULInt64("granule_position"),
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
    def packets(self):
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

    #an iterator which yields (Container,data string) tuples per pass
    #Container is parsed from OGGS
    #data string is a collection of segments as a string
    #(it may not be a complete packet)
    def pages(self):
        self.stream.seek(0,0)
        while (True):
            try:
                page = OggStreamReader.OGGS.parse_stream(self.stream)
                yield (page,self.stream.read(sum(page.segment_lengths)))
            except Con.core.FieldError:
                break

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
        
        page = Con.Container()
        page.magic_number = 'OggS'
        page.version = 0
        page.header_type = header_type
        page.granule_position = granule_position
        page.bitstream_serial_number = serial_number
        page.page_sequence_number = starting_sequence_number
        page.checksum = 0
        
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
                                   0)
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
                                   0)
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
#CD data
#######################

#keep in mind the whole of CD reading isn't remotely thread-safe
#due to the linear nature of CD access,
#reading from more than one track of a given CD at the same time
#is something code should avoid at all costs!
#there's simply no way to accomplish that cleanly

class CDDA:
    def __init__(self, device_name, speed=None):
        import cdio
        self.cdda = cdio.CDDA(device_name)
        self.total_tracks = self.cdda.total_tracks()
        if (speed != None):
            self.cdda.set_speed(speed)

    def __len__(self):
        return self.total_tracks

    def __getitem__(self, key):
        if ((key < 1) or (key > self.total_tracks)):
            raise IndexError(key)
        else:
            return CDTrackReader(self.cdda,int(key))

    def __iter__(self):
        for i in range(1,self.total_tracks + 1):
            yield self[i]

    def length(self):
        return self.cdda.length_in_seconds() * 75


class CDTrackLog(dict):
    #PARANOIA_CB_READ 	Read off adjust ???
    #PARANOIA_CB_VERIFY 	Verifying jitter
    #PARANOIA_CB_FIXUP_EDGE 	Fixed edge jitter
    #PARANOIA_CB_FIXUP_ATOM 	Fixed atom jitter
    #PARANOIA_CB_SCRATCH 	Unsupported
    #PARANOIA_CB_REPAIR 	Unsupported
    #PARANOIA_CB_SKIP 	Skip exhausted retry
    #PARANOIA_CB_DRIFT 	Skip exhausted retry
    #PARANOIA_CB_BACKOFF 	Unsupported
    #PARANOIA_CB_OVERLAP 	Dynamic overlap adjust
    #PARANOIA_CB_FIXUP_DROPPED 	Fixed dropped bytes
    #PARANOIA_CB_FIXUP_DUPED 	Fixed duplicate bytes
    #PARANOIA_CB_READERR 	Hard read error

    #log format is similar to cdda2wav's
    def __str__(self):
        return ", ".join(["%%(%s)d %s" % (field,field)
                          for field in 
                          ("rderr","skip","atom","edge",
                           "drop","dup","drift")]) % \
                           {"edge":self.get(2,0),
                            "atom":self.get(3,0),
                            "skip":self.get(6,0),
                            "drift":self.get(7,0),
                            "drop":self.get(10,0),
                            "dup":self.get(11,0),
                            "rderr":self.get(12,0)}


class CDTrackReader(PCMReader):
    #cdda is a cdio.CDDA object
    #track_number is which track this is from the disc, starting from 1
    def __init__(self, cdda, track_number):
        PCMReader.__init__(self, None,
                           sample_rate=44100,
                           channels=2,
                           bits_per_sample=16,
                           process=None)

        self.cdda = cdda
        self.track_number = track_number

        (self.__start__,self.__end__) = cdda.track_offsets(track_number)


        self.__position__ = self.__start__
        self.__cursor_placed__ = False

        self.rip_log = CDTrackLog()

    def offset(self):
        return self.__start__ + 150

    def length(self):
        return self.__end__ - self.__start__ + 1

    def log(self, i, v):
        if v in self.rip_log:
            self.rip_log[v] += 1
        else:
            self.rip_log[v] = 1


    def __read_sectors__(self, sectors):
        #if we haven't moved CDDA to the track start yet, do it now
        if (not self.__cursor_placed__):
            self.cdda.seek(self.__start__)
            cdio.set_read_callback(self.log)

            self.__position__ = self.__start__
            self.__cursor_placed__ = True

        if (self.__position__ <= self.__end__):
            s = self.cdda.read_sectors(min(sectors,
                                           self.__end__ - self.__position__ + 1))
            self.__position__ += sectors
            return s
        else:
            return ""

    def read(self, bytes):
        #returns a sector-aligned number of bytes
        #(divisible by 2352 bytes, basically)
        #or at least 1 sector's worth, if "bytes" is too small
        return self.__read_sectors__(max(bytes / 2352,1))
            

    def close(self):
        pass


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
        self.qt_stream = __Qt_Atom_Stream__(file(self.filename,"r"))

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

    def length(self):
        return (self.__length__ - 1024) / self.__sample_rate__ * 75

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
        f = file(self.filename,"w")
        f.write(new_file)
        f.close()

        f = file(self.filename,"r")
        self.qt_stream = __Qt_Atom_Stream__(f)
        

    def to_pcm(self):
        devnull = file(os.devnull,"a")

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

        devnull = file(os.devnull,"a")

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
                               stderr=devnull)

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

        MetaData.__init__(self,
                          track_name=meta_data.get('\xa9nam',[u''])[0],
                          track_number=trkn.track_number,
                          album_name=meta_data.get('\xa9alb',[u''])[0],
                          artist_name=meta_data.get('\xa9ART',[u''])[0],
                          performer_name=u'',
                          copyright=meta_data.get('cprt',[u''])[0],
                          year=u'')

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


#######################
#WavPack
#######################

class WavPackAudio(ApeTaggedAudio,AudioFile):
    SUFFIX = "wv"
    DEFAULT_COMPRESSION = "veryhigh"
    COMPRESSION_MODES = ("fast","standard","high","veryhigh")
    BINARIES = ("wavpack","wvunpack")


    HEADER = Con.Struct("wavpackheader",
                        Con.String("id",4),
                        Con.ULInt32("block_size"),
                        Con.ULInt16("version"),
                        Con.ULInt8("track_number"),
                        Con.ULInt8("index_number"),
                        Con.ULInt32("total_samples"),
                        Con.ULInt32("block_index"),
                        Con.ULInt32("block_samples"),
                        Con.Embed(
            Con.BitStruct("flags",
                          Con.Flag("floating_point_data"),
                          Con.Flag("hybrid_noise_shaping"),
                          Con.Flag("cross_channel_decorrelation"),
                          Con.Flag("joint_stereo"),
                          Con.Flag("hybrid_mode"),
                          Con.Flag("mono_output"),
                          Con.Bits("bits_per_sample",2),

                          Con.Bits("left_shift_data_low",3),
                          Con.Flag("final_block_in_sequence"),
                          Con.Flag("initial_block_in_sequence"),
                          Con.Flag("hybrid_noise_balanced"),
                          Con.Flag("hybrid_mode_control_bitrate"),
                          Con.Flag("extended_size_integers"),

                          Con.Bit("sampling_rate_low"),
                          Con.Bits("maximum_magnitude",5),
                          Con.Bits("left_shift_data_high",2),

                          Con.Flag("reserved2"),
                          Con.Flag("false_stereo"),
                          Con.Flag("use_IIR"),
                          Con.Bits("reserved1",2),
                          Con.Bits("sampling_rate_high",3)
                          )),
                        Con.ULInt32("crc"))

    BITS_PER_SAMPLE = (8,16,24,32)
    SAMPLING_RATE = (6000,  8000,  9600,   11025, 
                     12000, 16000, 22050,  24000,
                     32000, 44100, 48000,  64000, 
                     88200, 96000, 192000, 0)


    def __init__(self, filename):
        self.filename = filename
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_samples__ = 0

        self.__read_info__()

    @classmethod
    def is_type(cls, file):
        return file.read(4) == 'wvpk'

    def lossless(self):
        return True

    def __read_info__(self):
        f = file(self.filename)
        try:
            header = WavPackAudio.HEADER.parse(f.read(
                    WavPackAudio.HEADER.sizeof()))

            if (header.id != 'wvpk'):
                raise InvalidFile('wavpack header ID invalid')
        
            self.__samplerate__ = WavPackAudio.SAMPLING_RATE[
                (header.sampling_rate_high << 1) |
                header.sampling_rate_low]
            self.__bitspersample__ = WavPackAudio.BITS_PER_SAMPLE[
                header.bits_per_sample]
            self.__total_samples__ = header.total_samples

            self.__channels__ = 0

            #go through as many headers as necessary
            #to count the number of channels
            if (header.mono_output):
                self.__channels__ += 1
            else:
                self.__channels__ += 2

            while (not header.final_block_in_sequence):
                f.seek(header.block_size - 24,1)
                header = WavPackAudio.HEADER.parse(f.read(
                        WavPackAudio.HEADER.sizeof()))
                if (header.mono_output):
                    self.__channels__ += 1
                else:
                    self.__channels__ += 2
        finally:
            f.close()

    def bits_per_sample(self):
        return self.__bitspersample__

    def channels(self):
        return self.__channels__

    def total_samples(self):
        return self.__total_samples__

    def sample_rate(self):
        return self.__samplerate__
    
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import tempfile

        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        compression_param = {"fast":["-f"],
                             "standard":[],
                             "high":["-h"],
                             "veryhigh":["-hh"]}

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        w = WaveAudio.from_pcm(f.name, pcmreader)
        
        sub = subprocess.Popen([BIN['wavpack'],
                                w.filename] + \
                               compression_param[compression] + \
                               ['-q','-y','-o',
                                filename])
        sub.wait()

        del(w)
        f.close()
        return WavPackAudio(filename)

    def to_pcm(self):
        sub = subprocess.Popen([BIN['wvunpack'],
                                '-q',
                                self.filename,
                                '-o','-'],
                               stdout=subprocess.PIPE)

        return WaveReader(sub.stdout,
                          sample_rate=self.sample_rate(),
                          channels=self.channels(),
                          bits_per_sample=self.bits_per_sample(),
                          process=sub)

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]        

        if ((len(track_names) > 0) and
            BIN.can_execute(BIN['wvgain'])):
            devnull = file(os.devnull,'a')

            sub = subprocess.Popen([BIN['wvgain'],
                                    '-q','-a'] + track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()


#######################
#Musepack Audio
#######################
 

class MusepackAudio(ApeTaggedAudio,AudioFile):
    SUFFIX = "mpc"
    DEFAULT_COMPRESSION = "standard"
    COMPRESSION_MODES = ("telephone","thumb","radio","standard",
                         "extreme","insane","braindead")
    BINARIES = ('mppdec','mppenc')

    #not sure about some of the flag locations
    #Musepack's header is very unusual
    MUSEPACK_HEADER = Con.Struct('musepack_header',
                                 Con.String('signature',3),
                                 Con.Byte('version'),
                                 Con.ULInt32('frame_count'),
                                 Con.ULInt16('max_level'),
                                 Con.Embed(
        Con.BitStruct('flags',
                      Con.Bits('profile',4),
                      Con.Bits('link',2),
                      Con.Bits('sample_frequency',2),
                      Con.Flag('intensity_stereo'),
                      Con.Flag('midside_stereo'),
                      Con.Bits('maxband',6))),
                                 Con.ULInt16('title_gain'),
                                 Con.ULInt16('title_peak'),
                                 Con.ULInt16('album_gain'),
                                 Con.ULInt16('album_peak'),
                                 Con.Embed(
        Con.BitStruct('more_flags',
                      Con.Bits('unused1',16),
                      Con.Bits('last_frame_length_low',4),
                      Con.Flag('true_gapless'),
                      Con.Bits('unused2',3),
                      Con.Flag('fast_seeking'),
                      Con.Bits('last_frame_length_high',7))),
                                 Con.Bytes('unknown',3),
                                 Con.Byte('encoder_version'))

    def __init__(self, filename):
        AudioFile.__init__(self, filename)
        f = file(filename,'r')
        try:
            header = MusepackAudio.MUSEPACK_HEADER.parse_stream(f)
        finally:
            f.close()

        if (header.signature != 'MP+'):
            raise InvalidFile('musepack signature incorrect')

        header.last_frame_length = (header.last_frame_length_high << 4) | \
                                   header.last_frame_length_low

        self.__sample_rate__ = (44100,48000,
                                37800,32000)[header.sample_frequency]
        self.__total_samples__ = ((header.frame_count - 1 ) * 1152) + \
                                 header.last_frame_length

    def to_pcm(self):
        sub = subprocess.Popen([BIN['mppdec'],'--silent',
                                '--raw-le',
                                self.filename,'-'],
                               stdout=subprocess.PIPE)
        return PCMReader(sub.stdout,
                         sample_rate=self.sample_rate(),
                         channels=self.channels(),
                         bits_per_sample=self.bits_per_sample(),
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import tempfile

        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (pcmreader.sample_rate not in (44100,48000,37800,32000)):
            raise InvalidFormat(
                "Musepack only supports sample rates 44100, 48000, 37800 and 32000")

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        w = WaveAudio.from_pcm(f.name, pcmreader)
        sub = subprocess.Popen([BIN['mppenc'],
                                "--silent",
                                "--overwrite",
                                "--%s" % (compression),
                                w.filename,
                                filename])
        sub.wait()
        del(w)
        f.close()
        return MusepackAudio(filename)

    @classmethod
    def is_type(cls, file):
        return file.read(4) == 'MP+\x07'

    def sample_rate(self):
        return self.__sample_rate__

    def total_samples(self):
        return self.__total_samples__

    def channels(self):
        return 2

    def bits_per_sample(self):
        return 16

    def lossless(self):
        return False


#######################
#Multiple Jobs Handling
#######################

class ExecQueue:
    def __init__(self):
        self.todo = []

    #function is a Python function to apply
    #args is a tuple of arguments
    #kwargs, if not None, is a dict of additional keyword arguments
    def execute(self, function, args, kwargs=None):
        self.todo.append((function,args,kwargs))

    def __run__(self, function, args, kwargs):
        pid = os.fork()
        if (pid > 0):  #parent
            return pid
        else:          #child
            if (kwargs != None):
                function(*args,**kwargs)
            else:
                function(*args)
            sys.exit(0)

    #performs the queued actions in seperate subprocesses
    #"max_processes" number of times until the todo list is empty
    def run(self, max_processes=1):
        process_pool = set([])

        #fill the process_pool to the limit
        while ((len(self.todo) > 0) and (len(process_pool) < max_processes)):
            (function,args,kwargs) = self.todo.pop(0)
            process_pool.add(self.__run__(function,args,kwargs))
            #print "Filling %s" % (repr(process_pool))
        
        #as processes end, keep adding new ones to the pool
        #until we run out of queued jobs
        while (len(self.todo) > 0):
            try:
                process_pool.remove(os.waitpid(0,0)[0])
                (function,args,kwargs) = self.todo.pop(0)
                process_pool.add(self.__run__(function,args,kwargs))
                #print "Resuming %s" % (repr(process_pool))
            except KeyError:
                continue

        #finally, wait for the running jobs to finish
        while (len(process_pool) > 0):
            try:
                process_pool.remove(os.waitpid(0,0)[0])
                #print "Emptying %s" % (repr(process_pool))
            except KeyError:
                continue

#***ApeAudio temporarily removed***
#Without a legal alternative to mac-port, I shall have to re-implement
#Monkey's Audio with my own code in order to make it available again.
#Yet another reason to avoid that unpleasant file format...

AVAILABLE_TYPES = (FlacAudio,OggFlacAudio,
                   MP3Audio,MP2Audio,WaveAudio,
                   VorbisAudio,SpeexAudio,MusepackAudio,
                   AiffAudio,AuAudio,M4AAudio,WavPackAudio)

TYPE_MAP = dict([(track_type.SUFFIX,track_type) 
                 for track_type in AVAILABLE_TYPES
                 if track_type.has_binaries(BIN)]); del(track_type)
