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

import sys

if (sys.version_info < (2,5,0,'final',0)):
    print >>sys.stderr,"*** Python 2.5.0 or better required"
    sys.exit(1)


from . import construct as Con
from . import pcm as pcm
import subprocess
import re
import cStringIO
import os
import os.path
import ConfigParser
import optparse
import struct
from itertools import izip
import gettext

gettext.install("audiotools",unicode=True)


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
config.read([os.path.join("/etc","audiotools.cfg"),
             os.path.join(sys.prefix,"etc","audiotools.cfg"),
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
MUSICBRAINZ_SERVER = config.get_default("MusicBrainz","server",
                                        "musicbrainz.org")
MUSICBRAINZ_PORT = config.getint_default("MusicBrainz","port",80)

THUMBNAIL_FORMAT = config.get_default("Thumbnail","format","jpeg")
THUMBNAIL_SIZE = config.getint_default("Thumbnail","size",150)

VERSION = "2.14alpha3"

FILENAME_FORMAT = config.get_default(
    "Filenames","format",
    '%(track_number)2.2d - %(track_name)s.%(suffix)s')

FS_ENCODING = config.get_default("System","fs_encoding",
                                 sys.getfilesystemencoding())
if (FS_ENCODING is None):
    FS_ENCODING = 'UTF-8'

IO_ENCODING = config.get_default("System","io_encoding","UTF-8")

try:
    import cpucount
    MAX_CPUS = cpucount.cpucount()
except ImportError:
    MAX_CPUS = 1

if (config.has_option("System","maximum_jobs")):
    MAX_JOBS = config.getint_default("System","maximum_jobs",1)
else:
    MAX_JOBS = MAX_CPUS

BIG_ENDIAN = sys.byteorder == 'big'

def find_glade_file(glade_filename):
    glade_paths = [".",
                   os.path.join(sys.prefix,"share/audiotools"),
                   os.path.join("/usr","share/audiotools"),
                   os.path.join("/usr/local","share/audiotools")]

    for path in glade_paths:
        filename = os.path.join(path,glade_filename)
        if (os.path.isfile(filename)):
            return filename
    else:
        raise IOError(glade_filename)

#######################
#Output Messaging
#######################

class OptionParser(optparse.OptionParser):
    def _get_encoding(self,file):
        return IO_ENCODING

OptionGroup = optparse.OptionGroup

def Messenger(executable, options):
    if (not hasattr(options,"verbosity")):
        return VerboseMessenger(executable)
    elif ((options.verbosity == 'normal') or
          (options.verbosity == 'debug')):
        return VerboseMessenger(executable)
    else:
        return SilentMessenger(executable)

class __MessengerRow__:
    def __init__(self):
        self.strings = []    #a list of unicode strings
        self.alignments = [] #a list of booleans
                             #False if left-aligned, True if right-aligned
        self.total_lengths = [] #a list of total length integers,
                                #to be set at print-time

    def add_string(self,string,left_aligned):
        self.strings.append(string)
        self.alignments.append(left_aligned)
        self.total_lengths.append(len(string))

    def lengths(self):
        return map(len,self.strings)

    def set_total_lengths(self,total_lengths):
        self.total_lengths = total_lengths

    def __unicode__(self):
        output_string = []
        for (string,right_aligned,length) in zip(self.strings,
                                                self.alignments,
                                                self.total_lengths):
            if (len(string) < length):
                if (not right_aligned):
                    output_string.append(string)
                    output_string.append(u" " * (length - len(string)))
                else:
                    output_string.append(u" " * (length - len(string)))
                    output_string.append(string)
            else:
                output_string.append(string)
        return u"".join(output_string)

class VerboseMessenger:
    def __init__(self, executable):
        self.executable = executable
        self.output_msg_rows = []  #a list of __MessengerRow__ objects

    #displays an output message unicode string to stdout
    #and adds a newline
    def output(self,s):
        sys.stdout.write(s.encode(IO_ENCODING,'replace'))
        sys.stdout.write(os.linesep)

    #displays a partial output message unicode string to stdout
    #and flushes output so it is displayed
    def partial_output(self,s):
        sys.stdout.write(s.encode(IO_ENCODING,'replace'))
        sys.stdout.flush()

    #sets up a new tabbed row for outputting aligned text
    def new_row(self):
        self.output_msg_rows.append(__MessengerRow__())

    def blank_row(self):
        if (len(self.output_msg_rows) == 0):
            raise ValueError("first output row cannot be blank")
        else:
            self.new_row()
            for i in xrange(len(self.output_msg_rows[0].lengths())):
                self.output_column(u"")

    def output_column(self,string,right_aligned=False):
        if (len(self.output_msg_rows) > 0):
            self.output_msg_rows[-1].add_string(string,right_aligned)
        else:
            raise ValueError("you must perform \"new_row\" before adding columns")

    #outputs all of our accumulated output rows as aligned output
    def output_rows(self):
        lengths = [row.lengths() for row in self.output_msg_rows]
        if (len(lengths) == 0):
            raise ValueError("you must generate at least one output row")
        if (len(set(map(len,lengths))) != 1):
            raise ValueError("all output rows must be the same length")

        max_lengths = []
        for i in xrange(len(lengths[0])):
            max_lengths.append(max([length[i] for length in lengths]))

        for row in self.output_msg_rows:
            row.set_total_lengths(max_lengths)

        for row in self.output_msg_rows:
            self.output(unicode(row))
        self.output_msg_rows = []

    #displays an informative message unicode string to stderr
    #and adds a newline
    def info(self,s):
        sys.stderr.write(s.encode(IO_ENCODING,'replace'))
        sys.stderr.write(os.linesep)

    #displays a partial informative message unicode string to stderr
    #and flushes output so it is displayed
    def partial_info(self,s):
        sys.stderr.write(s.encode(IO_ENCODING,'replace'))
        sys.stderr.flush()

    #what's the difference between output() and info() ?
    #output() is for a program's primary data
    #info() is for incidental information
    #for example, trackinfo(1) should use output() for what it displays
    #since that output is its primary function
    #but track2track should use info() for its lines of progress
    #since its primary function is converting audio
    #and tty output is purely incidental

    #displays an error message unicode string
    #and adds a newline
    def error(self,s):
        sys.stderr.write("*** Error: ")
        sys.stderr.write(s.encode(IO_ENCODING,'replace'))
        sys.stderr.write(os.linesep)

    #displays an warning message unicode string
    #and adds a newline
    def warning(self,s):
        sys.stderr.write("*** Warning: ")
        sys.stderr.write(s.encode(IO_ENCODING,'replace'))
        sys.stderr.write(os.linesep)

    #displays the program's usage string to stderr
    #and adds a newline
    def usage(self,s):
        sys.stderr.write("*** Usage: ")
        sys.stderr.write(self.executable.decode('ascii'))
        sys.stderr.write(" ")
        sys.stderr.write(s.encode(IO_ENCODING,'replace'))
        sys.stderr.write(os.linesep)

    #takes a filename string and returns a unicode string
    #decoded according to the system's encoding
    def filename(self,s):
        return s.decode(FS_ENCODING,'replace')

class SilentMessenger(VerboseMessenger):
    def output(self,s):
        pass

    def partial_output(self,s):
        pass

    def warning(self,s):
        pass

    def info(self,s):
        pass

    def partial_info(self,s):
        pass


#raised by open() if the file cannot be identified or opened correctly
class UnsupportedFile(Exception): pass

#raised if an audio file cannot be initialized correctly
class InvalidFile(Exception): pass

#raised if an audio file cannot be created correctly from from_pcm()
#due to having a PCM format unsupported by the output format
class InvalidFormat(Exception): pass

#raised if an audio file cannot be created correctly from from_pcm()
#due to an error by the encoder
class EncodingError(IOError):
    def __init__(self,executable=None):
        self.executable = executable

    def __str__(self):
        return "error during file encoding"

class UnsupportedChannelMask(EncodingError):
    def __str__(self):
        return "unsupported channel mask during file encoding"

class DecodingError(IOError):
    def __str__(self):
        return "error during file decoding"

#takes a filename string
#returns a valid AudioFile object based on the file data or extension
#or raises UnsupportedFile if it's not a file we support
def open(filename):
    available_types = frozenset(TYPE_MAP.values())

    try:
        f = file(filename,"rb")
        try:
            for audioclass in TYPE_MAP.values():
                f.seek(0,0)
                if (audioclass.is_type(f)):
                    return audioclass(filename)
            else:
                raise UnsupportedFile(filename)

        finally:
            f.close()
    except IOError:
        raise UnsupportedFile(filename)

#takes a list of filenames
#returns a list of AudioFile objects, sorted by track_number()
#any unsupported files are filtered out
def open_files(filename_list, sorted=True):
    toreturn = []
    msg = Messenger("audiotools",None)

    for filename in filename_list:
        try:
            toreturn.append(open(filename))
        except UnsupportedFile:
            pass
        except InvalidFile,err:
            msg.error(unicode(err))

    if (sorted):
        toreturn.sort(lambda x,y: cmp((x.album_number(),x.track_number()),
                                      (y.album_number(),y.track_number())))
    return toreturn

#takes a root directory
#iterates recursively over any and all audio files in it
#optionally sorted by directory name and track_number()
#any unsupported files are filtered out
def open_directory(directory, sorted=True):
    for (basedir,subdirs,filenames) in os.walk(directory):
        if (sorted):
            subdirs.sort()
        for audiofile in open_files([os.path.join(basedir,filename)
                                     for filename in filenames],
                                    sorted=sorted):
            yield audiofile

#takes an iterable collection of tracks
#yields list of tracks grouped by album
#where their album_name and album_number match, if possible
def group_tracks(tracks):
    collection = {}
    for track in tracks:
        metadata = track.get_metadata()
        if (metadata is not None):
            collection.setdefault((track.album_number(),
                                   metadata.album_name),[]).append(track)
        else:
            collection.setdefault((track.album_number(),
                                   None),[]).append(track)
    for tracks in collection.values():
        yield tracks

class UnknownAudioType(Exception):
    def __init__(self,suffix):
        self.suffix = suffix

    def error_msg(self,messenger):
        messenger.error(_(u"Unsupported audio type \"%s\"") % (self.suffix))

class AmbiguousAudioType(UnknownAudioType):
    def __init__(self,suffix,type_list):
        self.suffix = suffix
        self.type_list = type_list

    def error_msg(self,messenger):
        messenger.error(_(u"Ambiguious suffix type \"%s\"") % (self.suffix))
        messenger.info(_(u"Please use the -t option to specify %s") % \
                           (" or ".join(["\"%s\"" % (t.NAME)
                                         for t in self.type_list])))

#given a path string to a file,
#try to guess its type based on suffix
#returns an available AudioFile
#raises an UnknownAudioType exception if the type is unknown
#raise AmbiguousAudioType exception if the type is ambiguous
def filename_to_type(path):
    (path,ext) = os.path.splitext(path)
    if (len(ext) > 0):
        ext = ext[1:]   #remove the "."
        SUFFIX_MAP = {}
        for audio_type in TYPE_MAP.values():
            SUFFIX_MAP.setdefault(audio_type.SUFFIX,[]).append(audio_type)
        if (ext in SUFFIX_MAP.keys()):
            if (len(SUFFIX_MAP[ext]) == 1):
                return SUFFIX_MAP[ext][0]
            else:
                raise AmbiguousAudioType(ext,SUFFIX_MAP[ext])
        else:
            raise UnknownAudioType(ext)
    else:
        return TYPE_MAP['wav']

#an integer-like class that abstracts a PCMReader's channel assignments
#All channels in a FrameList will be in RIFF WAVE order
#as a sensible convention.
#But which channel corresponds to which speaker is decided by this mask.
#For example, a 4 channel PCMReader with the channel mask 0x33
#corresponds to the bits 00110011
#reading those bits from right to left (least significant first)
#the "front_left", "front_right", "back_left", "back_right" speakers are set.
#Therefore, the PCMReader's 4 channel FrameLists are laid out as follows:
#
# channel 0 -> front_left
# channel 1 -> front_right
# channel 2 -> back_left
# channel 3 -> back_right
#
#since the "front_center" and "low_frequency" bits are not set,
#those channels are skipped in the returned FrameLists.
#
#Many formats store their channels internally in a different order.
#Their PCMReaders will be expected to reorder channels
#and set a ChannelMask matching this convention.
#And, their from_pcm() functions will be expected to reverse the process.
class ChannelMask:
    SPEAKER_TO_MASK = {"front_left":0x1,
                       "front_right":0x2,
                       "front_center":0x4,
                       "low_frequency":0x8,
                       "back_left":0x10,
                       "back_right":0x20,
                       "front_left_of_center":0x40,
                       "front_right_of_center":0x80,
                       "back_center":0x100,
                       "side_left":0x200,
                       "side_right":0x400,
                       "top_center":0x800,
                       "top_front_left":0x1000,
                       "top_front_center":0x2000,
                       "top_front_right":0x4000,
                       "top_back_left":0x8000,
                       "top_back_center":0x10000,
                       "top_back_right":0x20000}

    MASK_TO_SPEAKER = dict(map(reversed,map(list,SPEAKER_TO_MASK.items())))

    def __init__(self, mask):
        mask = int(mask)

        for (speaker,speaker_mask) in self.SPEAKER_TO_MASK.items():
            setattr(self,speaker,(mask & speaker_mask) != 0)

    def __repr__(self):
        return "ChannelMask(%s)" % \
            ",".join(["%s=%s" % (field,getattr(self,field))
                      for field in self.SPEAKER_TO_MASK.keys()
                      if (getattr(self,field))])

    def __int__(self):
        import operator

        return reduce(operator.or_,
                      [self.SPEAKER_TO_MASK[field] for field in
                       self.SPEAKER_TO_MASK.keys()
                       if getattr(self,field)],
                      0)

    def __eq__(self, v):
        return int(self) == int(v)

    def __ne__(self, v):
        return int(self) != int(v)

    def __len__(self):
        return sum([1 for field in self.SPEAKER_TO_MASK.keys()
                    if getattr(self,field)])

    #returns a list of speakers this mask contains
    #in the order in which they should appear in the PCM stream
    def channels(self):
        c = []
        for (mask,speaker) in sorted(self.MASK_TO_SPEAKER.items(),
                                     lambda x,y: cmp(x[0],y[0])):
            if (getattr(self,speaker)):
                c.append(speaker)

        return c

    #returns the index of the given channel name within this mask
    #for example, given the mask 0xB (fL, fR, LFE, but no fC)
    #index("low_frequency") will return 3
    #if the channel is not in this mask, raises ValueError
    def index(self, channel_name):
        return self.channels().index(channel_name)

    @classmethod
    def from_fields(cls,**fields):
        mask = cls(0)

        for (key,value) in fields.items():
            if (key in cls.SPEAKER_TO_MASK.keys()):
                setattr(mask,key,bool(value))

        return mask

    @classmethod
    def from_channels(cls, channel_count):
        if (channel_count == 2):
            return cls(0x3)
        elif (channel_count == 1):
            return cls(0x4)
        else:
            raise ValueError("ambiguous channel assignment")

#a class that wraps around a file object and generates pcm.FrameList objects
#sample rate, channels and bits per sample are integers
class PCMReader:
    def __init__(self, file,
                 sample_rate, channels, channel_mask, bits_per_sample,
                 process=None, signed=True, big_endian=False):
        self.file = file
        self.sample_rate = sample_rate
        self.channels = channels
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample
        self.process = process
        self.signed = signed
        self.big_endian = big_endian

    #Try to read a FrameList of size "bytes".
    #This is *not* guaranteed to read exactly that number of bytes.
    #It may return less (at the end of the stream, especially).
    #It may return more.
    #However, it must always return a non-empty FrameList until the
    #end of the PCM stream is reached.
    def read(self, bytes):
        bytes -= (bytes % (self.channels * self.bits_per_sample / 8))
        return pcm.FrameList(self.file.read(max(
                    bytes,self.channels * self.bits_per_sample / 8)),
                             self.channels,
                             self.bits_per_sample,
                             self.big_endian,
                             self.signed)

    def close(self):
        self.file.close()

        if (self.process is not None):
            if (self.process.wait() != 0):
                raise DecodingError()

class PCMReaderError(PCMReader):
    def read(self, bytes):
        return ""

    def close(self):
        raise DecodingError()

class ReorderedPCMReader:
    def __init__(self, pcmreader, channel_order):
        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.channel_order = channel_order

    def read(self, bytes):
        framelist = self.pcmreader.read(bytes)

        return pcm.from_channels([framelist.channel(channel)
                                  for channel in self.channel_order])


    def close(self):
        self.pcmreader.close()


#sends BUFFER_SIZE strings from from_function to to_function
#until the string is empty
def transfer_data(from_function, to_function):
    try:
        s = from_function(BUFFER_SIZE)
        while (len(s) > 0):
            to_function(s)
            s = from_function(BUFFER_SIZE)
    except IOError:
        #this usually means a broken pipe, so we can only hope
        #the data reader is closing down correctly
        pass

def transfer_framelist_data(pcmreader, to_function,
                            signed=True,big_endian=False):
    try:
        f = pcmreader.read(BUFFER_SIZE)
        while (len(f) > 0):
            to_function(f.to_bytes(big_endian,signed))
            f = pcmreader.read(BUFFER_SIZE)
    except IOError:
        #this usually means a broken pipe, so we can only hope
        #the data reader is closing down correctly
        pass

def threaded_transfer_framelist_data(pcmreader, to_function,
                                     signed=True,big_endian=False):
    import threading,Queue

    def send_data(pcmreader, queue):
        s = pcmreader.read(BUFFER_SIZE)
        while (len(s) > 0):
            queue.put(s)
            s = pcmreader.read(BUFFER_SIZE)
        queue.put(None)

    data_queue = Queue.Queue(10)
    #thread.start_new_thread(send_data,(from_function,data_queue))
    thread = threading.Thread(target=send_data,
                              args=(pcmreader,data_queue))
    thread.setDaemon(True)
    thread.start()
    s = data_queue.get()
    while (s is not None):
        to_function(s)
        s = data_queue.get()

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

class __capped_stream_reader__:
    #allows a maximum number of bytes "length" to
    #be read from file-like object "stream"
    #(used for reading IFF chunks, among others)
    def __init__(self, stream, length):
        self.stream = stream
        self.remaining = length

    def read(self, bytes):
        data = self.stream.read(min(bytes,self.remaining))
        self.remaining -= len(data)
        return data

    def close(self):
        self.stream.close()

#returns True if the PCM data in pcmreader1 equals pcmreader2
#False if there is any data mismatch
#the readers must be closed independently of this checker
def pcm_cmp(pcmreader1, pcmreader2):
    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return False

    reader1 = BufferedPCMReader(pcmreader1)
    reader2 = BufferedPCMReader(pcmreader2)

    s1 = reader1.read(BUFFER_SIZE)
    s2 = reader2.read(BUFFER_SIZE)

    while ((len(s1) > 0) and (len(s2) > 0)):
        if (s1 != s2):
            transfer_data(reader1.read,lambda x: x)
            transfer_data(reader2.read,lambda x: x)
            return False
        else:
            s1 = reader1.read(BUFFER_SIZE)
            s2 = reader2.read(BUFFER_SIZE)

    return True

#returns True if the PCM data in pcmreader1 equals pcmreader2
#not counting any 0x00 bytes at the beginning and end
#of each reader
def stripped_pcm_cmp(pcmreader1, pcmreader2):
    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return False

    try:
        from hashlib import sha1 as sha
    except ImportError:
        from sha import new as sha

    data = cStringIO.StringIO()

    d = pcmreader1.read(BUFFER_SIZE)
    while (len(d) > 0):
        data.write(d)
        d = pcmreader1.read(BUFFER_SIZE)

    sum1 = sha(data.getvalue().strip(chr(0x00)))

    data = cStringIO.StringIO()

    d = pcmreader2.read(BUFFER_SIZE)
    while (len(d) > 0):
        data.write(d)
        d = pcmreader2.read(BUFFER_SIZE)

    sum2 = sha(data.getvalue().strip(chr(0x00)))

    del(data)

    return sum1.digest() == sum2.digest()


class PCMCat(PCMReader):
    #takes an iterator of PCMReader objects
    #returns their data concatted together
    def __init__(self, pcmreaders):
        self.reader_queue = pcmreaders

        try:
            self.first = self.reader_queue.next()
        except StopIteration:
            raise ValueError(_(u"You must have at least 1 PCMReader"))

        self.sample_rate = self.first.sample_rate
        self.channels = self.first.channels
        self.channel_mask = self.first.channel_mask
        self.bits_per_sample = self.first.bits_per_sample

    def read(self, bytes):
        try:
            s = self.first.read(bytes)
            if (len(s) > 0):
                return s
            else:
                self.first.close()
                self.first = self.reader_queue.next()
                return self.read(bytes)
        except StopIteration:
            return pcm.from_list([],
                                 self.channels,
                                 self.bits_per_sample,
                                 True)

    def close(self):
        pass


class __buffer__:
    def __init__(self, channels, bits_per_sample, framelists=None):
        if (framelists is None):
            self.buffer = []
        else:
            self.buffer = framelists
        self.end_frame = pcm.from_list([],channels,bits_per_sample,True)
        self.bytes_per_sample = bits_per_sample / 8

    #returns the length of the entire buffer in bytes
    def __len__(self):
        if (len(self.buffer) > 0):
            return sum(map(len,self.buffer)) * self.bytes_per_sample
        else:
            return 0

    def framelist(self):
        import operator

        return reduce(operator.concat,self.buffer,self.end_frame)

    def push(self, s):
        self.buffer.append(s)

    def pop(self):
        return self.buffer.pop(0)

    def unpop(self, s):
        self.buffer.insert(0,s)

class BufferedPCMReader:
    def __init__(self, pcmreader):
        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.buffer = __buffer__(self.channels,self.bits_per_sample)
        self.reader_finished = False

    def close(self):
        self.pcmreader.close()

    def read(self, bytes):
        #fill our buffer to at least "bytes", possibly more
        self.__fill__(bytes)
        output_framelist = self.buffer.framelist()
        (output,remainder) = output_framelist.split(output_framelist.frame_count(bytes))
        self.buffer.buffer = [remainder]
        return output

    #try to fill our internal buffer to at least "bytes"
    def __fill__(self, bytes):
        while ((len(self.buffer) < bytes) and
               (not self.reader_finished)):
            s = self.pcmreader.read(BUFFER_SIZE)
            if (len(s) > 0):
                self.buffer.push(s)
            else:
                self.reader_finished = True



#takes a PCMReader and a list of reader lengths (in PCM samples)
#returns an iterator of PCMReader-compatible objects, each limited
#to the given lengths.
#The reader is closed upon completion
def pcm_split(reader, pcm_lengths):
    import tempfile

    def chunk_sizes(total_size,chunk_size):
        while (total_size > chunk_size):
            total_size -= chunk_size
            yield chunk_size
        yield total_size

    full_data = BufferedPCMReader(reader)

    for byte_length in [i * reader.channels * reader.bits_per_sample / 8
                        for i in pcm_lengths]:
        if (byte_length > (BUFFER_SIZE * 10)):
            #if the sub-file length is somewhat large, use a temporary file
            sub_file = tempfile.TemporaryFile()
            for size in chunk_sizes(byte_length,BUFFER_SIZE):
                sub_file.write(full_data.read(size).to_bytes(False,True))
            sub_file.seek(0,0)
        else:
            #if the sub-file length is very small, use StringIO
            sub_file = cStringIO.StringIO(full_data.read(byte_length).to_bytes(False,True))

        yield PCMReader(sub_file,
                        reader.sample_rate,
                        reader.channels,
                        reader.bits_per_sample)

    full_data.close()

#going from many channels to less channels
class __channel_remover__:
    def __init__(self, old_channel_mask, new_channel_mask):
        old_channels = ChannelMask(old_channel_mask).channels()
        self.channels_to_keep = []
        for new_channel in ChannelMask(new_channel_mask).channels():
            if (new_channel in old_channels):
                self.channels_to_keep.append(old_channels.index(new_channel))

    def convert(self, frame_list):
        return pcm.from_channels(
            [frame_list.channel(i) for i in self.channels_to_keep])

class __stereo_to_mono__:
    def __init__(self):
        pass

    def convert(self, frame_list):
        return pcm.from_list(
            [(l + r) / 2 for l,r in izip(frame_list.channel(0),
                                         frame_list.channel(1))],
            1,frame_list.bits_per_sample,True)

#going from many channels to 2
class __downmixer__:
    def __init__(self, old_channel_mask):
        #grab the front_left, front_right, front_center,
        #back_left and back_right channels from old frame_list, if possible
        #missing channels are replaced with 0-sample channels
        #excess channels are dropped entirely
        #side_left and side_right may be substituted for back_left/right
        #but back channels take precedence

        old_channel_mask = ChannelMask(old_channel_mask)

        #channels_to_keep is an array of channel offsets
        #where the index is:
        #0 - front_left
        #1 - front_right
        #2 - front_center
        #3 - back/side_left
        #4 - back/side_right
        #if -1, the channel is blank
        self.channels_to_keep = []
        for channel in ["front_left","front_right","front_center"]:
            if (getattr(old_channel_mask,channel)):
                self.channels_to_keep.append(old_channel_mask.index(channel))
            else:
                self.channels_to_keep.append(-1)

        if (old_channel_mask.back_left):
            self.channels_to_keep.append(old_channel_mask.index("back_left"))
        elif (old_channel_mask.side_left):
            self.channels_to_keep.append(old_channel_mask.index("side_left"))
        else:
            self.channels_to_keep.append(-1)

        if (old_channel_mask.back_right):
            self.channels_to_keep.append(old_channel_mask.index("back_right"))
        elif (old_channel_mask.side_right):
            self.channels_to_keep.append(old_channel_mask.index("side_right"))
        else:
            self.channels_to_keep.append(-1)

        self.has_empty_channels = (-1 in self.channels_to_keep)

    def convert(self, frame_list):
        REAR_GAIN = 0.6
        CENTER_GAIN = 0.7

        if (self.has_empty_channels):
            empty_channel = pcm.from_list([0] * frame_list.frames,
                                          1,
                                          frame_list.bits_per_sample,
                                          True)

        if (self.channels_to_keep[0] != -1):
            Lf = self_channels_to_keep[0]
        else:
            Lf = empty_channel

        if (self.channels_to_keep[1] != -1):
            Rf = self_channels_to_keep[1]
        else:
            Rf = empty_channel

        if (self.channels_to_keep[2] != -1):
            C = self_channels_to_keep[2]
        else:
            C = empty_channel

        if (self.channels_to_keep[3] != -1):
            Lr = self_channels_to_keep[3]
        else:
            Lr = empty_channel

        if (self.channels_to_keep[4] != -1):
            Rr = self_channels_to_keep[4]
        else:
            Rr = empty_channel

        mono_rear = [0.7 * (Lr_i + Rr_i) for Lr_i,Rr_i in izip(Lr,Rr)]

        converter = lambda x: int(round(x))

        left_channel = pcm.from_list(
            [converter(Lf_i +
                       (REAR_GAIN * mono_rear_i) +
                       (CENTER_GAIN * C_i))
             for Lf_i,mono_rear_i,C_i in izip(Lf,mono_rear,C)],
            1,
            frame_list.bits_per_sample,
            True)

        right_channel = pcm.from_list(
            [converter(Rf_i -
                       (REAR_GAIN * mono_rear_i) +
                       (CENTER_GAIN * C_i))
             for Rf_i,mono_rear_i,C_i in izip(Rf,mono_rear,C)],
            1,
            frame_list.bits_per_sample,
            True)

        return pcm.from_channels([left_channel,right_channel])

#going from many channels to 1
class __downmix_to_mono__:
    def __init__(self, old_channel_mask):
        self.downmix = __downmixer__(old_channel_mask)
        self.mono = __stereo_to_mono__()

    def convert(self, frame_list):
        return self.mono.convert(self.downmix.convert(frame_list))

class PCMConverter:
    def __init__(self, pcmreader,
                 sample_rate,
                 channels,
                 channel_mask,
                 bits_per_sample):
        import resample

        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.channel_mask = channel_mask
        self.reader = pcmreader

        self.conversions = []
        if (self.reader.channels != self.channels):
            if (self.channels == 1):
                self.conversions.append(
                    __downmix_to_mono__(pcmreader.channel_mask).convert)
            elif (self.channels == 2):
                self.conversions.append(
                    __downmixer__(pcmreader.channel_mask).convert)
            else:
                self.conversions.append(
                    __channel_remover__(pcmreader.channel_mask,
                                        channel_mask).convert)

        if (self.reader.sample_rate != self.sample_rate):
            self.resampler = resample.Resampler(
                self.channels,
                float(self.sample_rate) / float(self.reader.sample_rate),
                0)

            self.unresampled = pcm.FloatFrameList([],self.channels)

            #if we're converting sample rate and bits-per-sample
            #at the same time, short-circuit the conversion to do both at once
            #which can be sped up somewhat
            if (self.reader.bits_per_sample != self.bits_per_sample):
                self.conversions.append(self.convert_sample_rate_and_bits_per_sample)
            else:
                self.conversions.append(self.convert_sample_rate)

        else:
            if (self.reader.bits_per_sample != self.bits_per_sample):
                self.conversions.append(self.convert_bits_per_sample)


    def read(self, bytes):
        frame_list = self.reader.read(bytes)

        for converter in self.conversions:
            frame_list = converter(frame_list)

        return frame_list

    def close(self):
        self.reader.close()

    def convert_bits_per_sample(self, frame_list):
        #This modifies the bytes of "frame_list" in-place
        #rather than build a whole new array and return it.
        #Since our chained converters will overwrite the old frame_list
        #anyway, this should speed up the conversion without
        #damaging anything.
        #Just be careful when using this routine elsewhere.

        return self.add_dither(frame_list.to_float().to_int(self.bits_per_sample))

    def convert_channels(self, frame_list):
        difference = self.channels - self.reader.channels

        if (difference < 0): #removing channels

            #any channels above 6 are removed entirely
            if ((self.reader.channels > 6)):
                frame_list = pcm.from_channels([
                        frame_list.channel(i) for i in
                        xrange(6 + 1)])

            #return if we've removed all the channels necessary
            if (self.channels >= 6):
                return frame_list

            #otherwise, perform downmixing/channel removing
            #on the remaining set of channels
            return {2:{1:__stereo_to_mono__()},

                    3:{2:__downmixer__(),
                       1:__downmix_remover__()},

                    4:{3:__channel_remover__([0,1,2]),
                       2:__downmixer__(),
                       1:__downmix_remover__()},

                    5:{4:__channel_remover__([0,1,3,4]),
                       3:__channel_remover__([0,1,2]),
                       2:__downmixer__(),
                       1:__downmix_remover__()},

                    6:{5:__channel_remover__([0,1,2,4,5]),
                       4:__channel_remover__([0,1,4,5]),
                       3:__channel_remover__([0,1,2]),
                       2:__downmixer__(),
                       1:__downmix_remover__()},

                    7:{5:__channel_remover__([0,1,2,4,5]),
                       4:__channel_remover__([0,1,4,5]),
                       3:__channel_remover__([0,1,2]),
                       2:__downmixer__(),
                       1:__downmix_remover__()},

                    8:{5:__channel_remover__([0,1,2,4,5]),
                       4:__channel_remover__([0,1,4,5]),
                       3:__channel_remover__([0,1,2]),
                       2:__downmixer__(),
                       1:__downmix_remover__()}}[
                           self.reader.channels][
                               self.channels].convert(frame_list)

        else:                #adding new channels
            #we'll simply add more copies of the first channel
            #since this is typically going from mono to stereo
            channels = [frame_list.channel(i) for i in xrange(frame_list.channels)]
            for i in xrange(difference):
                channels.append(channels[0])

            return pcm.from_channels(channels)

    def convert_sample_rate(self, frame_list):
        #FIXME - The floating-point output from resampler.process()
        #should be normalized rather than just chopping off
        #excessively high or low samples (above 1.0 or below -1.0)
        #during conversion to PCM.
        #Unfortunately, that'll require building a second pass
        #into the conversion process which will complicate PCMConverter
        #a lot.
        (output,self.unresampled) = self.resampler.process(
            self.unresampled + frame_list.to_float(),
            (len(frame_list) == 0) and (len(self.unresampled) == 0))

        return output.to_int(self.bits_per_sample)


    #though this method name is huge, it is also unambiguous
    def convert_sample_rate_and_bits_per_sample(self, frame_list):
        (output,self.unresampled) = self.resampler.process(
            self.unresampled + frame_list.to_float(),
            (len(frame_list) == 0) and (len(self.unresampled) == 0))

        return self.add_dither(output.to_int(self.bits_per_sample))

    def add_dither(self, frame_list):
        if (frame_list.bits_per_sample >= 16):
            random_bytes = map(ord, os.urandom((len(frame_list) / 8) + 1))
            white_noise = [(random_bytes[i / 8] & (1 << (i % 8))) >> (i % 8)
                           for i in xrange(len(frame_list))]
        else:
            white_noise = [0] * len(frame_list)

        return pcm.from_list([i ^ w for (i,w) in izip(frame_list,
                                                      white_noise)],
                             frame_list.channels,
                             frame_list.bits_per_sample,
                             True)

#wraps around an existing PCMReader
#and applies ReplayGain upon calling the read() method
class ReplayGainReader:
    #pcmreader is a PCMReader-compatible object
    #replaygain is a floating point dB value
    #peak is a floating point value
    def __init__(self, pcmreader, replaygain, peak):
        self.reader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample

        self.replaygain = replaygain
        self.peak = peak
        self.bytes_per_sample = self.bits_per_sample / 8
        self.multiplier = 10 ** (replaygain / 20)

        #if we're increasing the volume (multipler is positive)
        #and that increases the peak beyond 1.0 (which causes clipping)
        #reduce the multiplier so that the peak doesn't go beyond 1.0
        if ((self.multiplier * self.peak) > 1.0):
            self.multiplier = 1.0 / self.peak

    def read(self, bytes):
        multiplier = self.multiplier
        samples = self.reader.read(bytes)

        if (self.bits_per_sample >= 16):
            random_bytes = map(ord, os.urandom((len(samples) / 8) + 1))
            white_noise = [(random_bytes[i / 8] & (1 << (i % 8))) >> (i % 8)
                           for i in xrange(len(samples))]
        else:
            white_noise = [0] * len(samples)

        return pcm.from_list(
            [(int(round(s * multiplier)) ^ w) for (s,w) in
             izip(samples,white_noise)],
            samples.channels,
            samples.bits_per_sample,
            True)

    def close(self):
        self.reader.close()

#given a list of tracks,
#returns an iterator of (track,track_gain,track_peak,album_gain,album_peak)
#tuples or raises ValueError if a problem occurs during calculation
def calculate_replay_gain(tracks):
    from . import replaygain as replaygain

    sample_rate = set([track.sample_rate() for track in tracks])
    if (len(sample_rate) != 1):
        raise ValueError("at least one track is required and all must have the same sample rate")
    rg = replaygain.ReplayGain(list(sample_rate)[0])
    gains = []
    for track in tracks:
        pcm = track.to_pcm()
        frame = pcm.read(BUFFER_SIZE)
        while (len(frame) > 0):
            rg.update(frame)
            frame = pcm.read(BUFFER_SIZE)
        pcm.close()
        (track_gain,track_peak) = rg.title_gain()
        gains.append((track,track_gain,track_peak))
    (album_gain,album_peak) = rg.album_gain()
    for (track,track_gain,track_peak) in gains:
        yield (track,track_gain,track_peak,album_gain,album_peak)

#this is a wrapper around another PCMReader meant for audio recording
#it runs read() continually in a separate thread
#it also traps SIGINT and stops reading when caught
class InterruptableReader(PCMReader):
    def __init__(self, pcmreader, verbose=True):
        import threading,Queue,signal

        PCMReader.__init__(self, pcmreader,
                           sample_rate=pcmreader.sample_rate,
                           channels=pcmreader.channels,
                           bits_per_sample=pcmreader.bits_per_sample)

        self.stop_reading = False
        self.data_queue = Queue.Queue()

        self.old_sigint = signal.signal(signal.SIGINT,self.stop)

        thread = threading.Thread(target=self.send_data)
        thread.setDaemon(True)
        thread.start()

        self.verbose = verbose

    def stop(self, *args):
        import signal

        self.stop_reading = True
        signal.signal(signal.SIGINT,self.old_sigint)

        if (self.verbose):
            print "Stopping..."

    def send_data(self):
        #try to use a half second long buffer
        BUFFER_SIZE = self.sample_rate * (self.bits_per_sample / 8) * \
                      self.channels / 2

        s = self.file.read(BUFFER_SIZE)
        while ((len(s) > 0) and (not self.stop_reading)):
            self.data_queue.put(s)
            s = self.file.read(BUFFER_SIZE)

        self.data_queue.put("")

    def read(self, length):
        return self.data_queue.get()

def ignore_sigint():
    import signal

    signal.signal(signal.SIGINT,signal.SIG_IGN)


#ensures all the directories leading to "destination_path" are created
#if necessary
#raises OSError if a problem occurs during directory creation
def make_dirs(destination_path):
    dirname = os.path.dirname(destination_path)
    if ((dirname != '') and (not os.path.isdir(dirname))):
        os.makedirs(dirname)

#######################
#Generic MetaData
#######################

class MetaData:
    __FIELDS__ = ("track_name","track_number","track_total",
                  "album_name","artist_name",
                  "performer_name","composer_name","conductor_name",
                  "media","ISRC","catalog","copyright",
                  "publisher","year","date","album_number","album_total",
                  "comment")

    __INTEGER_FIELDS__ = ("track_number","track_total",
                          "album_number","album_total")

    #track_name, album_name, artist_name, performer_name, copyright and year
    #should be unicode strings
    #track_number should be an integer
    def __init__(self,
                 track_name=u"",     #the name of this individual track
                 track_number=0,     #the number of this track
                 track_total=0,      #the total number of tracks
                 album_name=u"",     #the name of this track's album
                 artist_name=u"",    #the song's original creator/composer
                 performer_name=u"", #the song's performing artist
                 composer_name=u"",  #the song's composer name
                 conductor_name=u"", #the song's conductor's name
                 media=u"",          #the album's media type (CD,tape,LP,etc.)
                 ISRC=u"",           #the song's ISRC
                 catalog=u"",        #the album's catalog number
                 copyright=u"",      #the song's copyright information
                 publisher=u"",      #the song's publisher
                 year=u"",           #the album's release year
                 date=u"",           #the original recording date
                 album_number=0,     #the disc's volume number, if any
                 album_total=0,      #the total number of discs, if any
                 comment=u"",        #the track's comment string
                 images=None):
        #we're avoiding self.foo = foo because
        #__setattr__ might need to be redefined
        #which could lead to unwelcome side-effects
        self.__dict__['track_name'] = track_name
        self.__dict__['track_number'] = track_number
        self.__dict__['track_total'] = track_total
        self.__dict__['album_name'] = album_name
        self.__dict__['artist_name'] = artist_name
        self.__dict__['performer_name'] = performer_name
        self.__dict__['composer_name'] = composer_name
        self.__dict__['conductor_name'] = conductor_name
        self.__dict__['media'] = media
        self.__dict__['ISRC'] = ISRC
        self.__dict__['catalog'] = catalog
        self.__dict__['copyright'] = copyright
        self.__dict__['publisher'] = publisher
        self.__dict__['year'] = year
        self.__dict__['date'] = date
        self.__dict__['album_number'] = album_number
        self.__dict__['album_total'] = album_total
        self.__dict__['comment'] = comment

        if (images is not None):
            self.__dict__['__images__'] = list(images)
        else:
            self.__dict__['__images__'] = list()


    def __repr__(self):
        return ("MetaData(%s)" % (",".join(["%s"] * (len(MetaData.__FIELDS__))))) %\
            tuple(["%s=%s" % (field,repr(getattr(self,field)))
                   for field in MetaData.__FIELDS__])

    def __delattr__(self, field):
        if (field in self.__FIELDS__):
            if (field in self.__INTEGER_FIELDS__):
                self.__dict__[field] = 0
            else:
                self.__dict__[field] = u""
        else:
            try:
                del(self.__dict__[field])
            except KeyError:
                raise AttributeError(field)

    #returns the type of comment this is, as a unicode string
    def __comment_name__(self):
        return u'MetaData'

    #returns a list of (key,value) tuples
    def __comment_pairs__(self):
        return zip(("Title","Artist","Performer","Composer","Conductor",
                    "Album","Catalog",
                    "Track Number","Track Total",
                    "Volume Number","Volume Total",
                    "ISRC","Publisher","Media","Year","Date","Copyright",
                    "Comment"),
                   (self.track_name,
                    self.artist_name,
                    self.performer_name,
                    self.composer_name,
                    self.conductor_name,
                    self.album_name,
                    self.catalog,
                    str(self.track_number),
                    str(self.track_total),
                    str(self.album_number),
                    str(self.album_total),
                    self.ISRC,
                    self.publisher,
                    self.media,
                    self.year,
                    self.date,
                    self.copyright,
                    self.comment))

    def __unicode__(self):
        comment_pairs = self.__comment_pairs__()
        if (len(comment_pairs) > 0):
            max_key_length = max([len(pair[0]) for pair in comment_pairs])
            line_template = u"%%(key)%(length)d.%(length)ds : %%(value)s" % \
                            {"length":max_key_length}

            base_comment = unicode(os.linesep.join(
                [_(u"%s Comment:") % (self.__comment_name__())] + \
                [line_template % {"key":key,"value":value} for
                 (key,value) in comment_pairs]))
        else:
            base_comment = u""

        if (len(self.images()) > 0):
            return u"%s%s%s" % \
                   (base_comment,
                    os.linesep * 2,
                    os.linesep.join([unicode(p) for p in self.images()]))
        else:
            return base_comment

    def __eq__(self, metadata):
        if (metadata is not None):
            return set([(getattr(self,attr) == getattr(metadata,attr))
                        for attr in MetaData.__FIELDS__]) == set([True])
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
        if (metadata is not None):
            fields = dict([(field,getattr(metadata,field))
                           for field in cls.__FIELDS__])
            fields["images"] = metadata.images()
            return MetaData(**fields)
        else:
            return None


    #returns True if this particular sort of metadata support images
    #returns False if not
    @classmethod
    def supports_images(cls):
        return True

    def images(self):
        #must return a copy of our internal array
        #otherwise this will likely not act as expected when deleting
        return self.__images__[:]

    def front_covers(self):
        return [i for i in self.images() if i.type == 0]

    def back_covers(self):
        return [i for i in self.images() if i.type == 1]

    def leaflet_pages(self):
        return [i for i in self.images() if i.type == 2]

    def media_images(self):
        return [i for i in self.images() if i.type == 3]

    def other_images(self):
        return [i for i in self.images() if i.type == 4]

    #image should be an Image object
    #this method should also affect the underlying metadata value
    #(e.g. adding a new Image to FlacMetaData should add another
    # METADATA_BLOCK_PICTURE block to the metadata)
    def add_image(self, image):
        if (self.supports_images()):
            self.__images__.append(image)
        else:
            raise ValueError(_(u"This MetaData type does not support images"))

    #image should be an existing Image object
    #this method should also affect the underlying metadata value
    #(e.g. removing an existing Image from FlacMetaData should
    # remove that same METADATA_BLOCK_PICTURE block from the metadata)
    def delete_image(self, image):
        if (self.supports_images()):
            self.__images__.pop(self.__images__.index(image))
        else:
            raise ValueError(_(u"This MetaData type does not support images"))

    #updates any currectly empty entries from values taken from "metadata"
    def merge(self, metadata):
        if (metadata is None):
            return

        fields = {}
        for field in self.__FIELDS__:
            if (field not in self.__INTEGER_FIELDS__):
                if (len(getattr(self,field)) == 0):
                    setattr(self,field,getattr(metadata,field))
            else:
                if (getattr(self,field) == 0):
                    setattr(self,field,getattr(metadata,field))

        if ((len(self.images()) == 0) and self.supports_images()):
            for img in metadata.images():
                self.add_image(img)


class AlbumMetaData(dict):
    def __init__(self, metadata_iter):
        dict.__init__(self,
                      dict([(m.track_number,m) for m in
                            metadata_iter]))

    #returns a single MetaData object containing all
    #the consistent fields contained in the album
    def metadata(self):
        return MetaData(**dict([(field,list(items)[0])
                                for (field,items) in
                                [(field,
                                  set([getattr(track,field) for track
                                       in self.values()]))
                                 for field in MetaData.__FIELDS__]
                                if (len(items) == 1)]))

#a superclass of MetaData file exceptions
#such as XMCDException and MBXMLException
class MetaDataFileException(Exception):
    def __unicode__(self):
        return _(u"Invalid XMCD or MusicBrainz XML file")

#######################
#Image MetaData
#######################

#A simple image data container
class Image:
    #data is a string of the actual image data file
    #mime_type is a unicode string of the image's MIME type
    #width and height are integers of the images' dimensions
    #color_depth is the full depth of the image in bits
    #(24 for JPEG, 8 for GIF, etc.)
    #color_count is the number of colors used for palette images, or 0
    #description is a unicode string
    #type is an int
    #0 = front cover
    #1 = back cover
    #2 = leaflet page
    #3 = media
    #4 = other
    def __init__(self, data, mime_type, width, height,
                 color_depth, color_count, description, type):
        self.data = data
        self.mime_type = mime_type
        self.width = width
        self.height = height
        self.color_depth = color_depth
        self.color_count = color_count
        self.description = description
        self.type = type

    def suffix(self):
        return {"image/jpeg":"jpg",
                "image/jpg":"jpg",
                "image/gif":"gif",
                "image/png":"png",
                "image/x-ms-bmp":"bmp",
                "image/tiff":"tiff"}.get(self.mime_type,"bin")

    def type_string(self):
        return {0:"Front Cover",
                1:"Back Cover",
                2:"Leaflet Page",
                3:"Media",
                4:"Other"}.get(self.type,"Other")

    def __repr__(self):
        return "Image(mime_type=%s,width=%s,height=%s,color_depth=%s,color_count=%s,description=%s,type=%s,...)" % \
               (repr(self.mime_type),repr(self.width),repr(self.height),
                repr(self.color_depth),repr(self.color_count),
                repr(self.description),repr(self.type))

    def __unicode__(self):
        return u"Picture : %s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width,self.height,self.mime_type)

    #returns a new Image object from the data, description and type
    #raises InvalidImage if there is some error initializing
    @classmethod
    def new(cls, image_data, description, type):
        img = image_metrics(image_data)

        return Image(data=image_data,
                     mime_type=img.mime_type,
                     width=img.width,
                     height=img.height,
                     color_depth=img.bits_per_pixel,
                     color_count=img.color_count,
                     description=description,
                     type=type)

    #returns a new Image object in the given width, height and format
    def thumbnail(self, width, height, format):
        return Image.new(thumbnail_image(self.data, width, height, format),
                         self.description,self.type)

    def __eq__(self, image):
        if (image is not None):
            return set([(getattr(self,attr) == getattr(image,attr))
                        for attr in
                        ("data","mime_type","width","height",
                         "color_depth","color_count","description",
                         "type")]) == set([True])
        else:
            return False

    def __ne__(self, image):
        return not self.__eq__(image)

#######################
#ReplayGain Metadata
#######################

class ReplayGain:
    def __init__(self, track_gain, track_peak, album_gain, album_peak):
        self.track_gain = float(track_gain)
        self.track_peak = float(track_peak)
        self.album_gain = float(album_gain)
        self.album_peak = float(album_peak)

    def __repr__(self):
        return "ReplayGain(%s,%s,%s,%s)" % \
            (self.track_gain,self.track_peak,
             self.album_gain,self.album_peak)

    def __eq__(self, rg):
        return ((self.track_gain == rg.track_gain) and
                (self.track_peak == rg.track_peak) and
                (self.album_gain == rg.album_gain) and
                (self.album_peak == rg.album_peak))

    def __ne__(self, rg):
        return not self.__eq__(rg)


#######################
#Generic Audio File
#######################

#raised by AudioFile.track_name()
#if its format string contains unknown fields
class UnsupportedTracknameField(Exception):
    def __init__(self, field):
        self.field = field

    def error_msg(self,messenger):
        messenger.error(_(u"Unknown field \"%s\" in file format") % \
                            (self.field))
        messenger.info(_(u"Supported fields are:"))
        for field in sorted(MetaData.__FIELDS__ + \
                            ("album_track_number","suffix")):
            if (field == 'track_number'):
                messenger.info(u"%(track_number)2.2d")
            else:
                messenger.info(u"%%(%s)s" % (field))


class AudioFile:
    SUFFIX = ""
    NAME = ""
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

    #returns an integer number of bits per sample in this track
    def bits_per_sample(self):
        raise NotImplementedError()

    #returns an integer number of channels this track contains
    def channels(self):
        raise NotImplementedError()

    #returns a ChannelMask-compatible object
    def channel_mask(self):
        #WARNING - This only returns valid masks for 1 and 2 channel audio
        #anything over 2 channels raises a ValueError
        #since there isn't any standard on what those channels should be.
        #AudioFiles that support more than 2 channels should override
        #this method with one that returns the proper mask.
        return ChannelMask.from_channels(self.channels())

    #returns True if this track is lossless, False if not
    def lossless(self):
        raise NotImplementedError()

    #takes a MetaData-compatible object and sets this track's metadata
    #raises IOError if there's some problem writing the file
    def set_metadata(self, metadata):
        pass

    #returns a MetaData-compatible object, or None
    #raises IOError if there's some problem reading the file
    def get_metadata(self):
        return None

    #deletes the track's MetaData, removing or unsetting tags as necessary
    #raises IOError if there's some problem writing the file
    def delete_metadata(self):
        pass

    def total_frames(self):
        raise NotImplementedError()

    #returns the length of the audio in CD frames (1/75 of a second)
    def cd_frames(self):
        try:
            return (self.total_frames() * 75) / self.sample_rate()
        except ZeroDivisionError:
            return 0

    def sample_rate(self):
        raise NotImplementedError()


    #returns a PCMReader-compatible object
    def to_pcm(self):
        raise NotImplementedError()

    #takes a filename string
    #a PCMReader-compatible object
    #and an optional compression level string
    #returns a new object of this class
    #raises EncodingError if an error occurs during encoding
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        raise NotImplementedError()

    #writes the contents of this AudioFile to the given RIFF WAVE filename
    #raises EncodingError if an error occurs during decoding
    def to_wave(self, wave_filename):
        WaveAudio.from_pcm(wave_filename,self.to_pcm())

    #takes a filename string of our new file
    #a wave_filename string of an existing RIFF WAVE file
    #and an optional compression level string
    #returns a new object of this class
    #raises EncodingError if an error occurs during encoding
    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        return cls.from_pcm(
            filename, WaveAudio(wave_filename).to_pcm(),compression)

    #This method should return True if the format supports storing
    #non-audio RIFF chunks during compression/decompression.
    #If this returns True on both ends of a track conversion,
    #we should route our data though a WAVE file so that such
    #foreign chunks are not lost in the process.
    @classmethod
    def supports_foreign_riff_chunks(cls):
        return False

    #returns True if our file contains any foreign RIFF chunks
    def has_foreign_riff_chunks(self):
        return False

    #returns this track's number
    #first checking metadata
    #and then making our best-guess from the filename
    #if we come up empty, returns 0
    def track_number(self):
        metadata = self.get_metadata()
        if ((metadata is not None) and (metadata.track_number > 0)):
            return metadata.track_number
        else:
            try:
                return int(re.findall(r'\d{2,3}',
                                      os.path.basename(self.filename))[0]) % 100
            except IndexError:
                return 0

    #return this track's album number
    #first checking metadata
    #and then making our best-guess from the filename
    #if we come up empty, returns 0
    def album_number(self):
        metadata = self.get_metadata()
        if (metadata is not None):
            return metadata.album_number
        else:
            try:
                long_track_number = int(re.findall(
                        r'\d{3}',
                        os.path.basename(self.filename))[0])
                return long_track_number / 100
            except IndexError:
                return 0

    #given a track number integer,
    #MetaData-compatible object (or None)
    #and, optionally, a format string
    #returns a filename string with its fields filled-in
    #raises an UnsupportedTracknameField if the format string
    #contains invalid template fields
    @classmethod
    def track_name(cls, track_number, track_metadata,
                   album_number = 0,
                   format = FILENAME_FORMAT):
        try:
            if ((track_metadata is not None) and
                (cls not in (WaveAudio,AuAudio))):
                format_dict = {"track_number":track_number,
                               "album_number":track_metadata.album_number,
                               "track_total":track_metadata.track_total,
                               "album_total":track_metadata.album_total,
                               "suffix":cls.SUFFIX}

                if (album_number == 0):
                    format_dict["album_track_number"] = "%2.2d" % (track_number)
                else:
                    format_dict["album_track_number"] = "%d%2.2d" % \
                        (album_number,track_number)

                for field in track_metadata.__FIELDS__:
                    if ((field != "suffix") and
                        (field not in MetaData.__INTEGER_FIELDS__)):
                        format_dict[field] = getattr(
                            track_metadata,
                            field).replace('/','-').replace(chr(0),' ')

                return (format % format_dict).encode(FS_ENCODING,'replace')
            else:
                if (album_number == 0):
                    return "track%(track_number)2.2d.%(suffix)s" % \
                        {"track_number":track_number,
                         "suffix":cls.SUFFIX}
                else:
                    return "track%(album_number)d%(track_number)2.2d.%(suffix)s" % \
                        {"track_number":track_number,
                         "album_number":album_number,
                         "suffix":cls.SUFFIX}
        except KeyError,error:
            raise UnsupportedTracknameField(unicode(error.args[0]))

    #takes a list of filenames matching this AudioFile type
    #and adds the proper ReplayGain values to them
    #raises ValueError if some problem occurs during ReplayGain application
    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]

    #returns True if we have the necessary binaries to add ReplayGain
    #returns False if not
    @classmethod
    def can_add_replay_gain(cls):
        return False

    #returns True if applying ReplayGain is a lossless process
    #(i.e. the file itself is unmodified by the procedure)
    #returns False if not
    @classmethod
    def lossless_replay_gain(cls):
        return True

    #returns a ReplayGain-compatible object of our ReplayGain values
    #or None if we have no values
    def replay_gain(self):
        return None

    #takes a cuesheet-compatible object
    #with catalog(), ISRCs(), indexes(), and pcm_lengths() methods
    #sets this AudioFile's embedded cuesheet to that data, if possible
    #raises IOError if an error occurs setting the cuesheet
    def set_cuesheet(self,cuesheet):
        pass

    #returns a cuesheet-compatible object
    #or None if no cuesheet is embedded
    #raises IOError if an error occurs reading the file
    def get_cuesheet(self):
        return None

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
        return set([True] + \
                   [system_binaries.can_execute(system_binaries[command])
                    for command in cls.BINARIES]) == set([True])


class DummyAudioFile(AudioFile):
    def __init__(self, length, metadata, track_number=0):
        self.__length__ = length
        self.__metadata__ = metadata
        self.__track_number__ = track_number

        AudioFile.__init__(self,"")

    def get_metadata(self):
        return self.__metadata__

    def cd_frames(self):
        return self.__length__

    def track_number(self):
        return self.__track_number__

    def sample_rate(self):
        return 44100

    def total_frames(self):
        return (self.cd_frames() * self.sample_rate()) / 75

###########################
#Cuesheet/TOC file handling
###########################

#Cuesheets and TOC files are bundled into a unified Sheet interface

#a parent exception for CueException and TOCException
class SheetException(ValueError): pass

def read_sheet(filename):
    import toc
    import cue

    try:
        #try TOC first, since its CD_DA header makes it easier to spot
        return toc.read_tocfile(filename)
    except SheetException:
        return cue.read_cuesheet(filename)

def parse_timestamp(s):
    if (":" in s):
        (m,s,f) = map(int,s.split(":"))
        return (m * 60 * 75) + (s * 75) + f
    else:
        return int(s)

def build_timestamp(i):
    return "%2.2d:%2.2d:%2.2d" % ((i / 75) / 60,(i / 75) % 60,i % 75)

#given a cuesheet-compatible object and a total_frames integer
#return a unicode string formatted for use by MetaData's __unicode__ method
#for eventual display by trackinfo
def sheet_to_unicode(sheet,total_frames):
    #FIXME? - This (and pcm_lengths() in general) assumes all cuesheets
    #have a sample rate of 44100Hz.
    #It's difficult to envision a scenario in which this assumption doesn't hold
    #The point of cuesheets is to manage disc-based data as
    #"solid" archives which can be rewritten identically to the original
    #yet this only works for CD audio, which must always be 44100Hz.
    #DVD-Audio is encoded into AOB files which cannot be mapped to cuesheets
    #and SACD's DSD format is beyond the scope of these PCM-centric tools.

    ISRCs = sheet.ISRCs()

    tracks = unicode(os.linesep).join(
        [" Track %2.2d - %2.2d:%2.2d%s" % \
             (i + 1,
              length / 44100 / 60,
              length / 44100 % 60,
              (" (ISRC %s)" % (ISRCs[i + 1].decode('ascii','replace'))) if ((i + 1) in ISRCs.keys()) else u"")
         for (i,length) in enumerate(sheet.pcm_lengths(total_frames))])


    if ((sheet.catalog() is not None) and
        (len(sheet.catalog()) > 0)):
        return u"  Catalog - %s%s%s" % \
            (sheet.catalog().decode('ascii','replace'),
             os.linesep,tracks)
    else:
        return tracks


from __image__ import *

from __wav__ import *
from __au__ import *
from __vorbiscomment__ import *
from __flac__ import *

from __ape__ import *
from __id3__ import *
from __mp3__ import *
from __vorbis__ import *
from __m4a__ import *
from __wavpack__ import *
from __musepack__ import *
from __speex__ import *
from __aiff__ import *

#######################
#CD data
#######################

#keep in mind the whole of CD reading isn't remotely thread-safe
#due to the linear nature of CD access,
#reading from more than one track of a given CD at the same time
#is something code should avoid at all costs!
#there's simply no way to accomplish that cleanly

def CDDA(device_name,speed=None):
    offset = config.getint_default("System","cdrom_read_offset",0)
    if (offset == 0):
        return RawCDDA(device_name,speed)
    else:
        return OffsetCDDA(device_name,offset,speed)

class RawCDDA:
    def __init__(self, device_name, speed=None):
        import cdio
        self.cdda = cdio.CDDA(device_name)
        self.total_tracks = len([track_type for track_type in
                                 map(self.cdda.track_type,
                                     xrange(1,self.cdda.total_tracks() + 1))
                                 if (track_type == 0)])
        if (speed is not None):
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
        #lead-in should always be 150
        return self.last_sector() + 150 + 1

    def close(self):
        pass

    def first_sector(self):
        return self.cdda.first_sector()

    def last_sector(self):
        return self.cdda.last_sector()

def at_a_time(total,per):
    for i in xrange(total / per):
        yield per
    yield total % per

#a RawCDDA-compatible class which automatically applies sample offsets
#note that this blocks for a *long* time at instantiation time
#as it reads the whole CD to a temp file and applies the proper offset
class OffsetCDDA(RawCDDA):
    def __init__(self, device_name, sample_offset, speed=None):
        import cdio
        import tempfile

        self.cdda = cdio.CDDA(device_name)
        self.total_tracks = self.cdda.total_tracks()

        if (speed is not None):
            self.cdda.set_speed(speed)

        self.__temp__ = tempfile.TemporaryFile()
        self.__tracks__ = {}

        if (self.total_tracks == 0xFF):
            return

        if (sample_offset < 0):
            self.__temp__.write(chr(0) * (-sample_offset * 4))

        for tracknum in xrange(1,self.cdda.total_tracks() + 1):
            (start,end) = self.cdda.track_offsets(tracknum)
            trackreader = OffsetCDTrackReader(
                tracknum,
                self.__temp__,
                self.__temp__.tell() + (sample_offset * 4),
                start,
                end)

            self.cdda.seek(start)
            cdio.set_read_callback(trackreader.log)

            for sector_count in at_a_time(end - start,445):
                self.__temp__.write(
                    self.cdda.read_sectors(sector_count).to_bytes(False,True))

            self.__tracks__[tracknum] = trackreader

        if (sample_offset > 0):
            self.__temp__.write(chr(0) * (sample_offset * 4))

    def __getitem__(self, key):
        return self.__tracks__[key]

    def close(self):
        self.__temp__.close()


class CDTrackLog(dict):
    #PARANOIA_CB_READ           Read off adjust ???
    #PARANOIA_CB_VERIFY         Verifying jitter
    #PARANOIA_CB_FIXUP_EDGE     Fixed edge jitter
    #PARANOIA_CB_FIXUP_ATOM     Fixed atom jitter
    #PARANOIA_CB_SCRATCH        Unsupported
    #PARANOIA_CB_REPAIR         Unsupported
    #PARANOIA_CB_SKIP           Skip exhausted retry
    #PARANOIA_CB_DRIFT          Skip exhausted retry
    #PARANOIA_CB_BACKOFF        Unsupported
    #PARANOIA_CB_OVERLAP        Dynamic overlap adjust
    #PARANOIA_CB_FIXUP_DROPPED  Fixed dropped bytes
    #PARANOIA_CB_FIXUP_DUPED    Fixed duplicate bytes
    #PARANOIA_CB_READERR        Hard read error

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
        PCMReader.__init__(
            self, None,
            sample_rate=44100,
            channels=2,
            channel_mask=ChannelMask.from_fields(front_left=True,
                                                 front_right=True),
            bits_per_sample=16)

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
            return pcm.from_list([],2,16,True)

    def read(self, bytes):
        #returns a sector-aligned number of bytes
        #(divisible by 2352 bytes, basically)
        #or at least 1 sector's worth, if "bytes" is too small
        return self.__read_sectors__(max(bytes / 2352,1))


    def close(self):
        pass

class OffsetCDTrackReader(PCMReader):
    def __init__(self, track_number, temp_file,
                 byte_offset, sector_start, sector_end):
        PCMReader.__init__(
            self, None,
            sample_rate=44100,
            channels=2,
            channel_mask=ChannelMask.from_fields(front_left=True,
                                                 front_right=True),
            bits_per_sample=16,
            process=None)
        self.track_number = track_number
        self.rip_log = CDTrackLog()

        self.__file__ = temp_file
        self.__byte_offset__ = byte_offset
        self.__remaining_bytes__ = 0
        self.__start__ = sector_start
        self.__end__ = sector_end
        self.__cursor_placed__ = False

    def offset(self):
        return self.__start__ + 150

    def length(self):
        return self.__end__ - self.__start__ + 1

    def log(self, i, v):
        if v in self.rip_log:
            self.rip_log[v] += 1
        else:
            self.rip_log[v] = 1

    def read(self, bytes):
        if (bytes % 4):
            bytes -= (bytes % 4)

        if (not self.__cursor_placed__):
            self.__file__.seek(self.__byte_offset__,0)
            self.__remaining_bytes__ = (self.__end__ - self.__start__) * 2352
            self.__cursor_placed__ = True

        if (self.__remaining_bytes__ > 0):
            data = self.__file__.read(min(bytes,self.__remaining_bytes__))
            self.__remaining_bytes__ -= len(data)
            return pcm.FrameList(data,2,16,False,True)
        else:
            return pcm.FrameList("",2,16,False,True)

    def close(self):
        self.__cursor_placed__ = False

#returns the value in item_list which occurs most often
def __most_numerous__(item_list):
    counts = {}

    if (len(item_list) == 0):
        return ""

    for item in item_list:
        counts.setdefault(item,[]).append(item)

    return sorted([(item,len(counts[item])) for item in counts.keys()],
                  lambda x,y: cmp(x[1],y[1]))[-1][0]

from __freedb__ import *
from __musicbrainz__ import *

#takes an XMCD or MusicBrainz XML file
#returns an AlbumMetaData-compatible object
#or throws a MetaDataFileException exception subclass if an error occurs
def read_metadata_file(filename):
    #try XMCD first
    try:
        return XMCD.read(filename).metadata()
    except XMCDException:
        pass

    #then try MusicBrainz
    try:
        return MusicBrainzReleaseXML.read(filename).metadata()
    except MBXMLException:
        pass

    #otherwise, throw exception
    raise MetaDataFileException(filename)

#######################
#Multiple Jobs Handling
#######################

class ExecQueue:
    def __init__(self):
        self.todo = []
        self.return_values = set([])

    def execute(self, function, args, kwargs=None):
        self.todo.append((function,args,kwargs))

    def __run__(self, function, args, kwargs):
        pid = os.fork()
        if (pid > 0):  #parent
            return pid
        else:          #child
            if (kwargs is not None):
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
                (pid,return_value) = os.waitpid(0,0)
                process_pool.remove(pid)
                self.return_values.add(return_value)
                (function,args,kwargs) = self.todo.pop(0)
                process_pool.add(self.__run__(function,args,kwargs))
                #print "Resuming %s" % (repr(process_pool))
            except KeyError:
                continue

        #finally, wait for the running jobs to finish
        while (len(process_pool) > 0):
            try:
                (pid,return_value) = os.waitpid(0,0)
                process_pool.remove(pid)
                self.return_values.add(return_value)
                #print "Emptying %s" % (repr(process_pool))
            except KeyError:
                continue


#######################
#Bitstream Handling
#######################

class BitstreamReader:
    #byte_source should be a standard file-like object
    #with a read() method that returns strings of bytes
    #and a close() method
    def __init__(self, byte_source):
        from . import decoders

        self.byte_source = byte_source
        self.context = 0

        self.__read_bits__ = decoders.read_bits
        self.__read_unary__ = decoders.read_unary

    def byte_align(self):
        self.context = 0

    def read(self, bits):
        read_bits = self.__read_bits__
        accumulator = 0

        while (bits > 0):
            if (self.context == 0):
                self.context = 0x800 | ord(self.byte_source.read(1))

            if (bits > 8):
                result = read_bits(self.context,8)
            else:
                result = read_bits(self.context,bits)

            accumulator = (accumulator << ((result & 0xF00000) >> 20)) | \
              ((result & 0xFF000) >> 12)
            self.context = (result & 0xFFF)
            bits -= ((result & 0xF00000) >> 20)

        return accumulator

    def read_signed(self, bits):
        if (self.read(1)):              #negative
            return self.read(bits - 1) - (1 << (bits - 1))
        else:
            return self.read(bits - 1)  #positive

    def unary(self, stop_bit):
        if ((stop_bit != 0) and (stop_bit != 1)):
            raise ValueError("stop_bit must be 0 or 1")

        read_unary = self.__read_unary__
        accumulator = 0

        if (self.context == 0):
            self.context = 0x800 | ord(self.byte_source.read(1))

        result = read_unary(self.context,stop_bit)
        accumulator += ((result & 0xFF000) >> 12)
        self.context = result & 0xFFF

        while (result >> 24):
            if (self.context == 0):
                self.context = 0x800 | ord(self.byte_source.read(1))

            result = read_unary(self.context,stop_bit)
            accumulator += ((result & 0xFF000) >> 12)
            self.context = result & 0xFFF

        return accumulator

    def tell(self):
        return self.byte_source.tell()

    def close(self):
        self.byte_source.close()
        self.context = 0

class BitstreamWriter:
    #byte_sink should be a file-like object
    #with a write() method that takes a string of bytes
    #and a close() method
    def __init__(self, byte_sink):
        from . import encoders

        self.byte_sink = byte_sink
        self.context = 0

        self.__write_bits__ = encoders.write_bits
        self.__write_unary__ = encoders.write_unary

    def byte_align(self):
        self.write(7,0)
        self.context = 0

    def write(self, bits, value):
        while (bits > 0):
            #chop off up to 8 bits to write at a time
            if (bits > 8):
                bits_to_write = 8
            else:
                bits_to_write = bits

            value_to_write = value >> (bits - bits_to_write)

            #feed them through the jump table
            result = self.__write_bits__(self.context,
                                         value_to_write | (bits_to_write << 8))

            #write a byte if necessary
            if (result >> 18):
                self.byte_sink.write(chr((result >> 10) & 0xFF))

            #update the context
            self.context = result & 0x3FF

            #decrement the count and value
            value -= (value_to_write << (bits - bits_to_write))
            bits -= bits_to_write

    def write_signed(self, bits, value):
        if (value >= 0):
            self.write(1,0)
            self.write(bits - 1, value)
        else:
            self.write(1,1)
            self.write(bits - 1, value + (1 << (bits - 1)))

    def unary(self, stop_bit, value):
        #send continuation blocks until we get to 7 bits or less
        while (value >= 8):
            result = self.__write_unary__(self.context,(stop_bit << 4) | 0x08)
            if (result >> 18):
                self.byte_sink.write(chr((result >> 10) & 0xFF))

            self.context = result & 0x3FF
            value -= 8

        #finally, send the remaining value
        result = self.__write_unary__(self.context,(stop_bit << 4) | value)
        if (result >> 18):
            self.byte_sink.write(chr((result >> 10) & 0xFF))

        self.context = result & 0x3FF

    def tell(self):
        return self.byte_sink.tell()

    def close(self):
        self.byte_sink.close()
        self.context = 0


#***ApeAudio temporarily removed***
#Without a legal alternative to mac-port, I shall have to re-implement
#Monkey's Audio with my own code in order to make it available again.
#Yet another reason to avoid that unpleasant file format...

#***ALACAudio also temporarily removed***
#Though it mostly works, it's not yet stable in ffmpeg
#and doesn't pass all of the lossless unit tests.
#It's best to leave it disabled until it works properly.

AVAILABLE_TYPES = (FlacAudio,OggFlacAudio,
                   MP3Audio,MP2Audio,WaveAudio,
                   VorbisAudio,SpeexAudio,
                   AiffAudio,AuAudio,M4AAudio,AACAudio,
                   WavPackAudio)

TYPE_MAP = dict([(track_type.NAME,track_type)
                 for track_type in AVAILABLE_TYPES
                 if track_type.has_binaries(BIN)]); del(track_type)
