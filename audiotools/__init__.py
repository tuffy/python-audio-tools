#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

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

"""The core Python Audio Tools module."""

import sys

if (sys.version_info < (2, 5, 0, 'final', 0)):
    print >> sys.stderr, "*** Python 2.5.0 or better required"
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

gettext.install("audiotools", unicode=True)


class RawConfigParser(ConfigParser.RawConfigParser):
    """Extends RawConfigParser to provide additional methods."""

    def get_default(self, section, option, default):
        """Returns a default if option is not found in section."""

        try:
            return self.get(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

    def getboolean_default(self, section, option, default):
        """Returns a default if option is not found in section."""

        try:
            return self.getboolean(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

    def set_default(self, section, option, value):
        try:
            self.set(section, option, value)
        except ConfigParser.NoSectionError:
            self.add_section(section)
            self.set(section, option, value)

    def getint_default(self, section, option, default):
        """Returns a default int if option is not found in section."""

        try:
            return self.getint(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

config = RawConfigParser()
config.read([os.path.join("/etc", "audiotools.cfg"),
             os.path.join(sys.prefix, "etc", "audiotools.cfg"),
             os.path.expanduser('~/.audiotools.cfg')])

BUFFER_SIZE = 0x100000


class __system_binaries__:
    def __init__(self, config):
        self.config = config

    def __getitem__(self, command):
        try:
            return self.config.get("Binaries", command)
        except ConfigParser.NoSectionError:
            return command
        except ConfigParser.NoOptionError:
            return command

    def can_execute(self, command):
        if (os.sep in command):
            return os.access(command, os.X_OK)
        else:
            for path in os.environ.get('PATH', os.defpath).split(os.pathsep):
                if (os.access(os.path.join(path, command), os.X_OK)):
                    return True
            return False

BIN = __system_binaries__(config)

DEFAULT_CDROM = config.get_default("System", "cdrom", "/dev/cdrom")

FREEDB_SERVER = config.get_default("FreeDB", "server", "us.freedb.org")
FREEDB_PORT = config.getint_default("FreeDB", "port", 80)
MUSICBRAINZ_SERVER = config.get_default("MusicBrainz", "server",
                                        "musicbrainz.org")
MUSICBRAINZ_PORT = config.getint_default("MusicBrainz", "port", 80)

THUMBNAIL_FORMAT = config.get_default("Thumbnail", "format", "jpeg")
THUMBNAIL_SIZE = config.getint_default("Thumbnail", "size", 150)

VERSION = "2.17alpha3"

FILENAME_FORMAT = config.get_default(
    "Filenames", "format",
    '%(track_number)2.2d - %(track_name)s.%(suffix)s')

FS_ENCODING = config.get_default("System", "fs_encoding",
                                 sys.getfilesystemencoding())
if (FS_ENCODING is None):
    FS_ENCODING = 'UTF-8'

IO_ENCODING = config.get_default("System", "io_encoding", "UTF-8")

VERBOSITY_LEVELS = ("quiet", "normal", "debug")
DEFAULT_VERBOSITY = config.get_default("Defaults", "verbosity", "normal")
if (DEFAULT_VERBOSITY not in VERBOSITY_LEVELS):
    DEFAULT_VERBOSITY = "normal"

DEFAULT_TYPE = config.get_default("System", "default_type", "wav")

def __default_quality__(audio_type):
    quality = DEFAULT_QUALITY.get(audio_type, "")
    try:
        if (quality not in TYPE_MAP[audio_type].COMPRESSION_MODES):
            return TYPE_MAP[audio_type].DEFAULT_COMPRESSION
        else:
            return quality
    except KeyError:
        return ""

try:
    import cpucount
    MAX_CPUS = cpucount.cpucount()
except ImportError:
    MAX_CPUS = 1

if (config.has_option("System", "maximum_jobs")):
    MAX_JOBS = config.getint_default("System", "maximum_jobs", 1)
else:
    MAX_JOBS = MAX_CPUS

BIG_ENDIAN = sys.byteorder == 'big'

def get_umask():
    mask = os.umask(0)
    os.umask(mask)
    return mask


#######################
#Output Messaging
#######################


class OptionParser(optparse.OptionParser):
    """Extends OptionParser to use IO_ENCODING as text encoding.

    This ensures the encoding remains consistent if --help
    output is piped to a pager vs. sent to a tty.
    """

    def _get_encoding(self, file):
        return IO_ENCODING

OptionGroup = optparse.OptionGroup


def Messenger(executable, options):
    """Returns a Messenger object based on set verbosity level in options."""

    if (not hasattr(options, "verbosity")):
        return VerboseMessenger(executable)
    elif ((options.verbosity == 'normal') or
          (options.verbosity == 'debug')):
        return VerboseMessenger(executable)
    else:
        return SilentMessenger(executable)

__ANSI_SEQUENCE__ = re.compile(u"\u001B\[[0-9;]+m")


def str_width(s):
    """Returns the width of unicode string s, in characters.

    This accounts for multi-code Unicode characters
    as well as embedded ANSI sequences.
    """

    import unicodedata

    return len(unicodedata.normalize('NFC', __ANSI_SEQUENCE__.sub(u"", s)))


class __MessengerRow__:
    def __init__(self):
        self.strings = []  # a list of unicode strings
        self.alignments = []  # a list of booleans
                              # False if left-aligned, True if right-aligned
        self.total_lengths = []  # a list of total length integers,
                                 # to be set at print-time

    def add_string(self, string, left_aligned):
        self.strings.append(string)
        self.alignments.append(left_aligned)
        self.total_lengths.append(str_width(string))

    def lengths(self):
        return map(str_width, self.strings)

    def set_total_lengths(self, total_lengths):
        self.total_lengths = total_lengths

    def __unicode__(self):
        output_string = []
        for (string, right_aligned, length) in zip(self.strings,
                                                   self.alignments,
                                                   self.total_lengths):
            if (str_width(string) < length):
                if (not right_aligned):
                    output_string.append(string)
                    output_string.append(u" " * (length - str_width(string)))
                else:
                    output_string.append(u" " * (length - str_width(string)))
                    output_string.append(string)
            else:
                output_string.append(string)
        return u"".join(output_string)


class __DividerRow__:
    def __init__(self, dividers):
        self.dividers = dividers
        self.total_lengths = []

    def lengths(self):
        return [1 for x in self.dividers]

    def set_total_lengths(self, total_lengths):
        self.total_lengths = total_lengths

    def __unicode__(self):
        return u"".join([divider * length for (divider, length) in
                         zip(self.dividers, self.total_lengths)])


class VerboseMessenger:
    """This class is for displaying formatted output in a consistent way.

    It performs proper unicode string encoding based on IO_ENCODING,
    but can also display tabular data and ANSI-escaped data
    with less effort.
    """

    #a set of ANSI SGR codes
    RESET = 0
    BOLD = 1
    FAINT = 2
    ITALIC = 3
    UNDERLINE = 4
    BLINK_SLOW = 5
    BLINK_FAST = 6
    REVERSE = 7
    STRIKEOUT = 9
    FG_BLACK = 30
    FG_RED = 31
    FG_GREEN = 32
    FG_YELLOW = 33
    FG_BLUE = 34
    FG_MAGENTA = 35
    FG_CYAN = 36
    FG_WHITE = 37
    BG_BLACK = 40
    BG_RED = 41
    BG_GREEN = 42
    BG_YELLOW = 43
    BG_BLUE = 44
    BG_MAGENTA = 45
    BG_CYAN = 46
    BG_WHITE = 47

    def __init__(self, executable):
        """executable is a plain string of what script is being run.

        This is typically for use by the usage() method."""

        self.executable = executable
        self.output_msg_rows = []  # a list of __MessengerRow__ objects

    def output(self, s):
        """Displays an output message unicode string to stdout.

        This appends a newline to that message."""

        sys.stdout.write(s.encode(IO_ENCODING, 'replace'))
        sys.stdout.write(os.linesep)

    def partial_output(self, s):
        """Displays a partial output message unicode string to stdout.

        This flushes output so that message is displayed"""

        sys.stdout.write(s.encode(IO_ENCODING, 'replace'))
        sys.stdout.flush()

    def new_row(self):
        """Sets up a new tabbed row for outputting aligned text.

        This must be called prior to calling output_column()."""

        self.output_msg_rows.append(__MessengerRow__())

    def blank_row(self):
        """Generates a completely blank row of aligned text.

        This cannot be the first row of aligned text."""

        if (len(self.output_msg_rows) == 0):
            raise ValueError("first output row cannot be blank")
        else:
            self.new_row()
            for i in xrange(len(self.output_msg_rows[0].lengths())):
                self.output_column(u"")

    def divider_row(self, dividers):
        """Adds a row of unicode divider characters.

        There should be one character in dividers per output column.
        For example:
        >>> m = VerboseMessenger("audiotools")
        >>> m.new_row()
        >>> m.output_column(u'Foo')
        >>> m.output_column(u' ')
        >>> m.output_column(u'Bar')
        >>> m.divider_row([u'-',u' ',u'-'])
        >>> m.output_rows()
        Foo Bar
        --- ---

        """

        self.output_msg_rows.append(__DividerRow__(dividers))

    def output_column(self, string, right_aligned=False):
        """Adds a column of aligned unicode data."""

        if (len(self.output_msg_rows) > 0):
            self.output_msg_rows[-1].add_string(string, right_aligned)
        else:
            raise ValueError(
                "you must perform \"new_row\" before adding columns")

    def output_rows(self):
        """Outputs all of our accumulated output rows as aligned output.

        This operates by calling our output() method.
        Therefore, subclasses that have overridden output() to noops
        (silent messengers) will also have silent output_rows() methods.
        """

        lengths = [row.lengths() for row in self.output_msg_rows]
        if (len(lengths) == 0):
            raise ValueError("you must generate at least one output row")
        if (len(set(map(len, lengths))) != 1):
            raise ValueError("all output rows must be the same length")

        max_lengths = []
        for i in xrange(len(lengths[0])):
            max_lengths.append(max([length[i] for length in lengths]))

        for row in self.output_msg_rows:
            row.set_total_lengths(max_lengths)

        for row in self.output_msg_rows:
            self.output(unicode(row))
        self.output_msg_rows = []

    def info(self, s):
        """Displays an informative message unicode string to stderr.

        This appends a newline to that message."""

        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def info_rows(self):
        """Outputs all of our accumulated output rows as aligned info.

        This operates by calling our info() method.
        Therefore, subclasses that have overridden info() to noops
        (silent messengers) will also have silent info_rows() methods.
        """

        lengths = [row.lengths() for row in self.output_msg_rows]
        if (len(lengths) == 0):
            raise ValueError("you must generate at least one output row")
        if (len(set(map(len, lengths))) != 1):
            raise ValueError("all output rows must be the same length")

        max_lengths = []
        for i in xrange(len(lengths[0])):
            max_lengths.append(max([length[i] for length in lengths]))

        for row in self.output_msg_rows:
            row.set_total_lengths(max_lengths)

        for row in self.output_msg_rows:
            self.info(unicode(row))
        self.output_msg_rows = []

    def partial_info(self, s):
        """Displays a partial informative message unicode string to stdout.

        This flushes output so that message is displayed"""

        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.flush()

    #what's the difference between output() and info() ?
    #output() is for a program's primary data
    #info() is for incidental information
    #for example, trackinfo(1) should use output() for what it displays
    #since that output is its primary function
    #but track2track should use info() for its lines of progress
    #since its primary function is converting audio
    #and tty output is purely incidental

    def error(self, s):
        """Displays an error message unicode string to stderr.

        This appends a newline to that message."""

        sys.stderr.write("*** Error: ")
        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def os_error(self, oserror):
        """Displays an properly formatted OSError exception to stderr.

        This appends a newline to that message."""

        self.error(u"[Errno %d] %s: '%s'" % \
                       (oserror.errno,
                        oserror.strerror.decode('utf-8', 'replace'),
                        self.filename(oserror.filename)))

    def warning(self, s):
        """Displays a warning message unicode string to stderr.

        This appends a newline to that message."""

        sys.stderr.write("*** Warning: ")
        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def usage(self, s):
        """Displays the program's usage unicode string to stderr.

        This appends a newline to that message."""

        sys.stderr.write("*** Usage: ")
        sys.stderr.write(self.executable.decode('ascii'))
        sys.stderr.write(" ")
        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def filename(self, s):
        """Decodes a filename string to unicode.

        This uses the system's encoding to perform translation."""

        return s.decode(FS_ENCODING, 'replace')

    def ansi(self, s, codes):
        """Generates an ANSI code as a unicode string.

        Takes a unicode string to be escaped
        and a list of ANSI SGR codes.
        Returns an ANSI-escaped unicode terminal string
        with those codes activated followed by the unescaped code
        if the Messenger's stdout is to a tty terminal.
        Otherwise, the string is returned unmodified.

        For example:
        >>> VerboseMessenger("audiotools").ansi(u"foo",
        ...                                     [VerboseMessenger.BOLD])
        u'\x1b[1mfoo\x1b[0m'
        """

        if (sys.stdout.isatty()):
            return u"\u001B[%sm%s\u001B[0m" % \
                (";".join(map(unicode, codes)), s)
        else:
            return s

    def ansi_clearline(self):
        """Generates a set of clear line ANSI escape codes to stdout.

        This works only if stdout is a tty.  Otherwise, it does nothing.
        For example:
        >>> msg = VerboseMessenger("audiotools")
        >>> msg.partial_output(u"working")
        >>> time.sleep(1)
        >>> msg.ansi_clearline()
        >>> msg.output(u"done")
        """

        if (sys.stdout.isatty()):
            sys.stdout.write((u"\u001B[0G" + #move cursor to column 0
                              u"\u001B[0K"   #clear everything after cursor
                              ).encode(IO_ENCODING))
            sys.stdout.flush()

    def ansi_err(self, s, codes):
        """Generates an ANSI code as a unicode string.

        Takes a unicode string to be escaped
        and a list of ANSI SGR codes.
        Returns an ANSI-escaped unicode terminal string
        with those codes activated followed by the unescapde code
        if the Messenger's stderr is to a tty terminal.
        Otherwise, the string is returned unmodified."""

        if (sys.stderr.isatty()):
            return u"\u001B[%sm%s\u001B[0m" % \
                (";".join(map(unicode, codes)), s)
        else:
            return s


class SilentMessenger(VerboseMessenger):
    def output(self, s):
        """Performs no output, resulting in silence."""

        pass

    def partial_output(self, s):
        """Performs no output, resulting in silence."""

        pass

    def warning(self, s):
        """Performs no output, resulting in silence."""

        pass

    def info(self, s):
        """Performs no output, resulting in silence."""

        pass

    def partial_info(self, s):
        """Performs no output, resulting in silence."""

        pass

    def ansi_clearline(self):
        """Performs no output, resulting in silence."""

        pass


class UnsupportedFile(Exception):
    """Raised by open() if the file can be opened but not identified."""

    pass


class InvalidFile(Exception):
    """Raised during initialization if the file is invalid in some way."""

    pass


class InvalidFormat(Exception):
    """Raised if an audio file cannot be created correctly from from_pcm()
    due to having a PCM format unsupported by the output format."""

    pass


class EncodingError(IOError):
    """Raised if an audio file cannot be created correctly from from_pcm()
    due to an error by the encoder."""

    def __init__(self, error_message):
        IOError.__init__(self)
        self.error_message = error_message

    def __str__(self):
        if (isinstance(self.error_message, unicode)):
            return self.error_message.encode('ascii', 'replace')
        else:
            return str(self.error_message)

    def __unicode__(self):
        return unicode(self.error_message)


class UnsupportedChannelMask(EncodingError):
    """Raised if the encoder does not support the file's channel mask."""

    def __init__(self):
        EncodingError.__init__(self,
            u"unsupported channel mask during file encoding")


class UnsupportedChannelCount(EncodingError):
    """Raised if the encoder does not support the file's channel count."""

    def __init__(self):
        EncodingError.__init__(self,
            u"unsupported channel count during file encoding")


class UnsupportedBitsPerSample(EncodingError):
    """Raised if the encoder does not support the file's bits-per-sample."""

    def __init__(self):
        EncodingError.__init__(self,
            u"unsupported bits per sample during file encoding")


class DecodingError(IOError):
    """Raised if the decoder exits with an error.

    Typically, a from_pcm() method will catch this error
    and raise EncodingError."""

    def __init__(self, error_message):
        IOError.__init__(self)
        self.error_message = error_message


def open(filename):
    """Returns an AudioFile located at the given filename path.

    This works solely by examining the file's contents
    after opening it.
    Raises UnsupportedFile if it's not a file we support based on its headers.
    Raises InvalidFile if the file appears to be something we support,
    but has errors of some sort.
    Raises IOError if some problem occurs attempting to open the file.
    """

    available_types = frozenset(TYPE_MAP.values())

    f = file(filename, "rb")
    try:
        for audioclass in TYPE_MAP.values():
            f.seek(0, 0)
            if (audioclass.is_type(f)):
                return audioclass(filename)
        else:
            raise UnsupportedFile(filename)

    finally:
        f.close()


#takes a list of filenames
#returns a list of AudioFile objects, sorted by track_number()
#any unsupported files are filtered out
def open_files(filename_list, sorted=True, messenger=None):
    """Returns a list of AudioFile objects from a list of filenames.

    Files are sorted by album number then track number, by default.
    Unsupported files are filtered out.
    Error messages are sent to messenger, if given.
    """

    toreturn = []
    if (messenger is None):
        messenger = Messenger("audiotools", None)

    for filename in filename_list:
        try:
            toreturn.append(open(filename))
        except UnsupportedFile:
            pass
        except IOError, err:
            messenger.warning(
                _(u"Unable to open \"%s\"" % (messenger.filename(filename))))
        except InvalidFile, err:
            messenger.error(unicode(err))

    if (sorted):
        toreturn.sort(lambda x, y: cmp((x.album_number(), x.track_number()),
                                       (y.album_number(), y.track_number())))
    return toreturn


#takes a root directory
#iterates recursively over any and all audio files in it
#optionally sorted by directory name and track_number()
#any unsupported files are filtered out
def open_directory(directory, sorted=True, messenger=None):
    """Yields an AudioFile via a recursive search of directory.

    Files are sorted by album number/track number by default,
    on a per-directory basis.
    Any unsupported files are filtered out.
    Error messages are sent to messenger, if given.
    """

    for (basedir, subdirs, filenames) in os.walk(directory):
        if (sorted):
            subdirs.sort()
        for audiofile in open_files([os.path.join(basedir, filename)
                                     for filename in filenames],
                                    sorted=sorted,
                                    messenger=messenger):
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
                                   metadata.album_name), []).append(track)
        else:
            collection.setdefault((track.album_number(),
                                   None), []).append(track)
    for tracks in collection.values():
        yield tracks


class UnknownAudioType(Exception):
    """Raised if filename_to_type finds no possibilities.."""

    def __init__(self, suffix):
        self.suffix = suffix

    def error_msg(self, messenger):
        messenger.error(_(u"Unsupported audio type \"%s\"") % (self.suffix))


class AmbiguousAudioType(UnknownAudioType):
    """Raised if filename_to_type finds more than one possibility."""

    def __init__(self, suffix, type_list):
        self.suffix = suffix
        self.type_list = type_list

    def error_msg(self, messenger):
        messenger.error(_(u"Ambiguious suffix type \"%s\"") % (self.suffix))
        messenger.info((_(u"Please use the -t option to specify %s") %
                        (u" or ".join([u"\"%s\"" % (t.NAME.decode('ascii'))
                                       for t in self.type_list]))))


def filename_to_type(path):
    """Given a path to a file, return its audio type based on suffix.

    For example:
    >>> filename_to_type("/foo/file.flac")
    <class audiotools.__flac__.FlacAudio at 0x7fc8456d55f0>

    Raises an UnknownAudioType exception if the type is unknown.
    Raise AmbiguousAudioType exception if the type is ambiguous.
    """

    (path, ext) = os.path.splitext(path)
    if (len(ext) > 0):
        ext = ext[1:]   # remove the "."
        SUFFIX_MAP = {}
        for audio_type in TYPE_MAP.values():
            SUFFIX_MAP.setdefault(audio_type.SUFFIX, []).append(audio_type)
        if (ext in SUFFIX_MAP.keys()):
            if (len(SUFFIX_MAP[ext]) == 1):
                return SUFFIX_MAP[ext][0]
            else:
                raise AmbiguousAudioType(ext, SUFFIX_MAP[ext])
        else:
            raise UnknownAudioType(ext)
    else:
        raise UnknownAudioType(ext)


class ChannelMask:
    """An integer-like class that abstracts a PCMReader's channel assignments

    All channels in a FrameList will be in RIFF WAVE order
    as a sensible convention.
    But which channel corresponds to which speaker is decided by this mask.
    For example, a 4 channel PCMReader with the channel mask 0x33
    corresponds to the bits 00110011
    reading those bits from right to left (least significant first)
    the "front_left", "front_right", "back_left", "back_right"
    speakers are set.

    Therefore, the PCMReader's 4 channel FrameLists are laid out as follows:

    channel 0 -> front_left
    channel 1 -> front_right
    channel 2 -> back_left
    channel 3 -> back_right

    since the "front_center" and "low_frequency" bits are not set,
    those channels are skipped in the returned FrameLists.

    Many formats store their channels internally in a different order.
    Their PCMReaders will be expected to reorder channels
    and set a ChannelMask matching this convention.
    And, their from_pcm() functions will be expected to reverse the process.

    A ChannelMask of 0 is "undefined",
    which means that channels aren't assigned to *any* speaker.
    This is an ugly last resort for handling formats
    where multi-channel assignments aren't properly defined.
    In this case, a from_pcm() method is free to assign the undefined channels
    any way it likes, and is under no obligation to keep them undefined
    when passing back out to to_pcm()
    """

    SPEAKER_TO_MASK = {"front_left": 0x1,
                       "front_right": 0x2,
                       "front_center": 0x4,
                       "low_frequency": 0x8,
                       "back_left": 0x10,
                       "back_right": 0x20,
                       "front_left_of_center": 0x40,
                       "front_right_of_center": 0x80,
                       "back_center": 0x100,
                       "side_left": 0x200,
                       "side_right": 0x400,
                       "top_center": 0x800,
                       "top_front_left": 0x1000,
                       "top_front_center": 0x2000,
                       "top_front_right": 0x4000,
                       "top_back_left": 0x8000,
                       "top_back_center": 0x10000,
                       "top_back_right": 0x20000}

    MASK_TO_SPEAKER = dict(map(reversed, map(list, SPEAKER_TO_MASK.items())))

    def __init__(self, mask):
        """mask should be an integer channel mask value."""

        mask = int(mask)

        for (speaker, speaker_mask) in self.SPEAKER_TO_MASK.items():
            setattr(self, speaker, (mask & speaker_mask) != 0)

    def __repr__(self):
        return "ChannelMask(%s)" % \
            ",".join(["%s=%s" % (field, getattr(self, field))
                      for field in self.SPEAKER_TO_MASK.keys()
                      if (getattr(self, field))])

    def __int__(self):
        import operator

        return reduce(operator.or_,
                      [self.SPEAKER_TO_MASK[field] for field in
                       self.SPEAKER_TO_MASK.keys()
                       if getattr(self, field)],
                      0)

    def __eq__(self, v):
        return int(self) == int(v)

    def __ne__(self, v):
        return int(self) != int(v)

    def __len__(self):
        return sum([1 for field in self.SPEAKER_TO_MASK.keys()
                    if getattr(self, field)])

    def defined(self):
        """Returns True if this ChannelMask is defined."""

        return int(self) != 0

    def undefined(self):
        """Returns True if this ChannelMask is undefined."""

        return int(self) == 0

    def channels(self):
        """Returns a list of speaker strings this mask contains.

        Returned in the order in which they should appear
        in the PCM stream.
        """

        c = []
        for (mask, speaker) in sorted(self.MASK_TO_SPEAKER.items(),
                                      lambda x, y: cmp(x[0], y[0])):
            if (getattr(self, speaker)):
                c.append(speaker)

        return c

    def index(self, channel_name):
        """Returns the index of the given channel name within this mask.

        For example, given the mask 0xB (fL, fR, LFE, but no fC)
        index("low_frequency") will return 2.
        If the channel is not in this mask, raises ValueError."""

        return self.channels().index(channel_name)

    @classmethod
    def from_fields(cls, **fields):
        """Given a set of channel arguments, returns a new ChannelMask.

        For example:
        >>> ChannelMask.from_fields(front_left=True,front_right=True)
        ChannelMask(front_right=True,front_left=True)
        """

        mask = cls(0)

        for (key, value) in fields.items():
            if (key in cls.SPEAKER_TO_MASK.keys()):
                setattr(mask, key, bool(value))
            else:
                raise KeyError(key)

        return mask

    @classmethod
    def from_channels(cls, channel_count):
        """Given a channel count, returns a new ChannelMask.

        This is only valid for channel counts 1 and 2.
        All other values trigger a ValueError."""

        if (channel_count == 2):
            return cls(0x3)
        elif (channel_count == 1):
            return cls(0x4)
        else:
            raise ValueError("ambiguous channel assignment")


class PCMReader:
    """A class that wraps around a file object and generates pcm.FrameLists"""

    def __init__(self, file,
                 sample_rate, channels, channel_mask, bits_per_sample,
                 process=None, signed=True, big_endian=False):
        """Fields are as follows:

        file            - a file-like object with read() and close() methods
        sample_rate     - an integer number of Hz
        channels        - an integer number of channels
        channel_mask    - an integer channel mask value
        bits_per_sample - an integer number of bits per sample
        process         - an optional subprocess object
        signed          - True if the file's samples are signed integers
        big_endian      - True if the file's samples are stored big-endian

        The process, signed and big_endian arguments are optional.
        PCMReader-compatible objects need only expose the
        sample_rate, channels, channel_mask and bits_per_sample fields
        along with the read() and close() methods.
        """

        self.file = file
        self.sample_rate = sample_rate
        self.channels = channels
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample
        self.process = process
        self.signed = signed
        self.big_endian = big_endian

    def read(self, bytes):
        """Try to read a pcm.FrameList of size "bytes".

        This is *not* guaranteed to read exactly that number of bytes.
        It may return less (at the end of the stream, especially).
        It may return more.
        However, it must always return a non-empty FrameList until the
        end of the PCM stream is reached.

        May raise IOError if unable to read the input file,
        or ValueError if the input file has some sort of error.
        """

        bytes -= (bytes % (self.channels * self.bits_per_sample / 8))
        return pcm.FrameList(self.file.read(max(
                    bytes, self.channels * self.bits_per_sample / 8)),
                             self.channels,
                             self.bits_per_sample,
                             self.big_endian,
                             self.signed)

    def close(self):
        """Closes the stream for reading.

        Any subprocess is waited for also so for proper cleanup.
        May return DecodingError if a helper subprocess exits
        with an error status."""

        self.file.close()

        if (self.process is not None):
            if (self.process.wait() != 0):
                raise DecodingError(u"subprocess exited with error")


class PCMReaderError(PCMReader):
    """A dummy PCMReader which automatically raises DecodingError.

    This is to be returned by an AudioFile's to_pcm() method
    if some error occurs when initializing a decoder.
    An encoder's from_pcm() method will then catch the DecodingError
    at close()-time and propogate an EncodingError."""

    def __init__(self, error_message,
                 sample_rate, channels, channel_mask, bits_per_sample):
        PCMReader.__init__(self, None, sample_rate, channels, channel_mask,
                           bits_per_sample)
        self.error_message = error_message

    def read(self, bytes):
        """Always returns an empty framelist."""

        return pcm.from_list([],
                             self.channels,
                             self.bits_per_sample,
                             True)

    def close(self):
        """Always raises DecodingError."""

        raise DecodingError(self.error_message)


class ReorderedPCMReader:
    """A PCMReader wrapper which reorders its output channels."""

    def __init__(self, pcmreader, channel_order):
        """Initialized with a PCMReader and list of channel number integers.

        For example, to swap the channels of a stereo stream:
        >>> ReorderedPCMReader(reader,[1,0])
        """

        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.channel_order = channel_order

    def read(self, bytes):
        """Try to read a pcm.FrameList of size "bytes"."""

        framelist = self.pcmreader.read(bytes)

        return pcm.from_channels([framelist.channel(channel)
                                  for channel in self.channel_order])

    def close(self):
        """Closes the stream."""

        self.pcmreader.close()


def transfer_data(from_function, to_function):
    """Sends BUFFER_SIZE strings from from_function to to_function.

    This continues until an empty string is returned from from_function."""

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
                            signed=True, big_endian=False):
    """Sends pcm.FrameLists from pcmreader to to_function.

    FrameLists are converted to strings using the signed and big_endian
    arguments.  This continues until an empty FrameLists is returned
    from pcmreader.
    """

    f = pcmreader.read(BUFFER_SIZE)
    while (len(f) > 0):
        to_function(f.to_bytes(big_endian, signed))
        f = pcmreader.read(BUFFER_SIZE)


def threaded_transfer_framelist_data(pcmreader, to_function,
                                     signed=True, big_endian=False):
    """Sends pcm.FrameLists from pcmreader to to_function via threads.

    FrameLists are converted to strings using the signed and big_endian
    arguments.  This continues until an empty FrameLists is returned
    from pcmreader.  It operates by splitting reading and writing
    into threads in the hopes that an intermittant reader
    will not disrupt the writer.
    """

    import threading
    import Queue

    def send_data(pcmreader, queue):
        try:
            s = pcmreader.read(BUFFER_SIZE)
            while (len(s) > 0):
                queue.put(s)
                s = pcmreader.read(BUFFER_SIZE)
            queue.put(None)
        except (IOError, ValueError):
            queue.put(None)

    data_queue = Queue.Queue(10)
    #thread.start_new_thread(send_data,(from_function,data_queue))
    thread = threading.Thread(target=send_data,
                              args=(pcmreader, data_queue))
    thread.setDaemon(True)
    thread.start()
    s = data_queue.get()
    while (s is not None):
        to_function(s)
        s = data_queue.get()


class __capped_stream_reader__:
    #allows a maximum number of bytes "length" to
    #be read from file-like object "stream"
    #(used for reading IFF chunks, among others)
    def __init__(self, stream, length):
        self.stream = stream
        self.remaining = length

    def read(self, bytes):
        data = self.stream.read(min(bytes, self.remaining))
        self.remaining -= len(data)
        return data

    def close(self):
        self.stream.close()


def pcm_cmp(pcmreader1, pcmreader2):
    """Returns True if the PCM data in pcmreader1 equals pcmreader2.

    The readers must be closed separately.
    """

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
            transfer_data(reader1.read, lambda x: x)
            transfer_data(reader2.read, lambda x: x)
            return False
        else:
            s1 = reader1.read(BUFFER_SIZE)
            s2 = reader2.read(BUFFER_SIZE)

    return True


def stripped_pcm_cmp(pcmreader1, pcmreader2):
    """Returns True if the stripped PCM data of pcmreader1 equals pcmreader2.

    This operates by reading each PCM streams entirely to memory,
    performing strip() on their output and comparing checksums
    (which permits us to store just one big blob of memory at a time).
    """

    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return False

    try:
        from hashlib import sha1 as sha
    except ImportError:
        from sha import new as sha

    data = cStringIO.StringIO()
    transfer_framelist_data(pcmreader1, data.write)
    sum1 = sha(data.getvalue().strip(chr(0x00)))

    data = cStringIO.StringIO()
    transfer_framelist_data(pcmreader2, data.write)
    sum2 = sha(data.getvalue().strip(chr(0x00)))

    del(data)

    return sum1.digest() == sum2.digest()


def pcm_frame_cmp(pcmreader1, pcmreader2):
    """Returns the PCM Frame number of the first mismatch.

    If the two streams match completely, returns None.
    May raise IOError or ValueError if problems occur
    when reading PCM streams."""

    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return 0

    if ((pcmreader1.channel_mask != 0) and
        (pcmreader2.channel_mask != 0) and
        (pcmreader1.channel_mask != pcmreader2.channel_mask)):
        return 0

    frame_number = 0
    reader1 = BufferedPCMReader(pcmreader1)
    reader2 = BufferedPCMReader(pcmreader2)

    framelist1 = reader1.read(BUFFER_SIZE)
    framelist2 = reader2.read(BUFFER_SIZE)

    while ((len(framelist1) > 0) and (len(framelist2) > 0)):
        if (framelist1 != framelist2):
            for i in xrange(min(framelist1.frames, framelist2.frames)):
                if (framelist1.frame(i) != framelist2.frame(i)):
                    return frame_number + i
            else:
                return frame_number + i
        else:
            frame_number += framelist1.frames
            framelist1 = reader1.read(BUFFER_SIZE)
            framelist2 = reader2.read(BUFFER_SIZE)

    return None


class PCMCat(PCMReader):
    """A PCMReader for concatenating several PCMReaders."""

    def __init__(self, pcmreaders):
        """pcmreaders is an iterator of PCMReader objects.

        Note that this currently does no error checking
        to ensure reads have the same sample_rate, channels,
        bits_per_sample or channel mask!
        One must perform that check prior to building a PCMCat.
        """

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
        """Try to read a pcm.FrameList of size "bytes"."""

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
        """Closes the stream for reading."""

        pass


class __buffer__:
    def __init__(self, channels, bits_per_sample, framelists=None):
        if (framelists is None):
            self.buffer = []
        else:
            self.buffer = framelists
        self.end_frame = pcm.from_list([], channels, bits_per_sample, True)
        self.bytes_per_sample = bits_per_sample / 8

    #returns the length of the entire buffer in bytes
    def __len__(self):
        if (len(self.buffer) > 0):
            return sum(map(len, self.buffer)) * self.bytes_per_sample
        else:
            return 0

    def framelist(self):
        import operator

        return reduce(operator.concat, self.buffer, self.end_frame)

    def push(self, s):
        self.buffer.append(s)

    def pop(self):
        return self.buffer.pop(0)

    def unpop(self, s):
        self.buffer.insert(0, s)


class BufferedPCMReader:
    """A PCMReader which reads exact counts of bytes."""

    def __init__(self, pcmreader):
        """pcmreader is a regular PCMReader object."""

        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.buffer = __buffer__(self.channels, self.bits_per_sample)
        self.reader_finished = False

    def close(self):
        """Closes the sub-pcmreader and frees our internal buffer."""

        del(self.buffer)
        self.pcmreader.close()

    def read(self, bytes):
        """Reads as close to "bytes" number of bytes without going over.

        This uses an internal buffer to ensure reading the proper
        number of bytes on each call.
        """

        #fill our buffer to at least "bytes", possibly more
        self.__fill__(bytes)
        output_framelist = self.buffer.framelist()
        (output, remainder) = output_framelist.split(
            output_framelist.frame_count(bytes))
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

class LimitedPCMReader:
    def __init__(self, buffered_pcmreader, total_pcm_frames):
        """buffered_pcmreader should be a BufferedPCMReader

        which ensures we won't pull more frames off the reader
        than necessary upon calls to read()"""

        self.pcmreader = buffered_pcmreader
        self.total_pcm_frames = total_pcm_frames
        self.sample_rate = self.pcmreader.sample_rate
        self.channels = self.pcmreader.channels
        self.channel_mask = self.pcmreader.channel_mask
        self.bits_per_sample = self.pcmreader.bits_per_sample
        self.bytes_per_frame = self.channels * (self.bits_per_sample / 8)

    def read(self, bytes):
        if (self.total_pcm_frames > 0):
            frame = self.pcmreader.read(
                min(bytes,
                    self.total_pcm_frames * self.bytes_per_frame))
            self.total_pcm_frames -= frame.frames
            return frame
        else:
            return pcm.FrameList("", self.channels, self.bits_per_sample,
                                 False, True)

    def close(self):
        self.total_pcm_frames = 0

def pcm_split(reader, pcm_lengths):
    """Yields a PCMReader object from reader for each pcm_length (in frames).

    Each sub-reader is pcm_length PCM frames long with the same
    channels, bits_per_sample, sample_rate and channel_mask
    as the full stream.  reader is closed upon completion.
    """

    import tempfile

    def chunk_sizes(total_size, chunk_size):
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
            for size in chunk_sizes(byte_length, BUFFER_SIZE):
                sub_file.write(full_data.read(size).to_bytes(False, True))
            sub_file.seek(0, 0)
        else:
            #if the sub-file length is very small, use StringIO
            sub_file = cStringIO.StringIO(
                full_data.read(byte_length).to_bytes(False, True))

        yield PCMReader(sub_file,
                        reader.sample_rate,
                        reader.channels,
                        reader.channel_mask,
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


class __channel_adder__:
    def __init__(self, channels):
        self.channels = channels

    def convert(self, frame_list):
        current_channels = [frame_list.channel(i)
                            for i in xrange(frame_list.channels)]
        while (len(current_channels) < self.channels):
            current_channels.append(current_channels[0])

        return pcm.from_channels(current_channels)


class __stereo_to_mono__:
    def __init__(self):
        pass

    def convert(self, frame_list):
        return pcm.from_list(
            [(l + r) / 2 for l, r in izip(frame_list.channel(0),
                                          frame_list.channel(1))],
            1, frame_list.bits_per_sample, True)


#going from many channels to 2
class __downmixer__:
    def __init__(self, old_channel_mask, old_channel_count):
        #grab the front_left, front_right, front_center,
        #back_left and back_right channels from old frame_list, if possible
        #missing channels are replaced with 0-sample channels
        #excess channels are dropped entirely
        #side_left and side_right may be substituted for back_left/right
        #but back channels take precedence

        if (int(old_channel_mask) == 0):
            #if the old_channel_mask is undefined
            #invent a channel mask based on the channel count
            old_channel_mask = {1: ChannelMask.from_fields(front_center=True),
                                2: ChannelMask.from_fields(front_left=True,
                                                           front_right=True),
                                3: ChannelMask.from_fields(front_left=True,
                                                           front_right=True,
                                                          front_center=True),
                                4: ChannelMask.from_fields(front_left=True,
                                                           front_right=True,
                                                           back_left=True,
                                                           back_right=True),
                                5: ChannelMask.from_fields(front_left=True,
                                                           front_right=True,
                                                           front_center=True,
                                                           back_left=True,
                                                           back_right=True)}[
                min(old_channel_count, 5)]
        else:
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
        for channel in ["front_left", "front_right", "front_center"]:
            if (getattr(old_channel_mask, channel)):
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
            Lf = frame_list.channel(self.channels_to_keep[0])
        else:
            Lf = empty_channel

        if (self.channels_to_keep[1] != -1):
            Rf = frame_list.channel(self.channels_to_keep[1])
        else:
            Rf = empty_channel

        if (self.channels_to_keep[2] != -1):
            C = frame_list.channel(self.channels_to_keep[2])
        else:
            C = empty_channel

        if (self.channels_to_keep[3] != -1):
            Lr = frame_list.channel(self.channels_to_keep[3])
        else:
            Lr = empty_channel

        if (self.channels_to_keep[4] != -1):
            Rr = frame_list.channel(self.channels_to_keep[4])
        else:
            Rr = empty_channel

        mono_rear = [0.7 * (Lr_i + Rr_i) for Lr_i, Rr_i in izip(Lr, Rr)]

        converter = lambda x: int(round(x))

        left_channel = pcm.from_list(
            [converter(Lf_i +
                       (REAR_GAIN * mono_rear_i) +
                       (CENTER_GAIN * C_i))
             for Lf_i, mono_rear_i, C_i in izip(Lf, mono_rear, C)],
            1,
            frame_list.bits_per_sample,
            True)

        right_channel = pcm.from_list(
            [converter(Rf_i -
                       (REAR_GAIN * mono_rear_i) +
                       (CENTER_GAIN * C_i))
             for Rf_i, mono_rear_i, C_i in izip(Rf, mono_rear, C)],
            1,
            frame_list.bits_per_sample,
            True)

        return pcm.from_channels([left_channel, right_channel])


#going from many channels to 1
class __downmix_to_mono__:
    def __init__(self, old_channel_mask, old_channel_count):
        self.downmix = __downmixer__(old_channel_mask, old_channel_count)
        self.mono = __stereo_to_mono__()

    def convert(self, frame_list):
        return self.mono.convert(self.downmix.convert(frame_list))


class __convert_sample_rate__:
    def __init__(self, old_sample_rate, new_sample_rate,
                 channels, bits_per_sample):
        from . import resample

        self.resampler = resample.Resampler(
                channels,
                float(new_sample_rate) / float(old_sample_rate),
                0)
        self.unresampled = pcm.FloatFrameList([], channels)
        self.bits_per_sample = bits_per_sample

    def convert(self, frame_list):
        #FIXME - The floating-point output from resampler.process()
        #should be normalized rather than just chopping off
        #excessively high or low samples (above 1.0 or below -1.0)
        #during conversion to PCM.
        #Unfortunately, that'll require building a second pass
        #into the conversion process which will complicate PCMConverter
        #a lot.
        (output, self.unresampled) = self.resampler.process(
            self.unresampled + frame_list.to_float(),
            (len(frame_list) == 0) and (len(self.unresampled) == 0))

        return output.to_int(self.bits_per_sample)


class __convert_sample_rate_and_bits_per_sample__(__convert_sample_rate__):
    def convert(self, frame_list):
        (output, self.unresampled) = self.resampler.process(
            self.unresampled + frame_list.to_float(),
            (len(frame_list) == 0) and (len(self.unresampled) == 0))

        return __add_dither__(output.to_int(self.bits_per_sample))


class __convert_bits_per_sample__:
    def __init__(self, bits_per_sample):
        self.bits_per_sample = bits_per_sample

    def convert(self, frame_list):
        return __add_dither__(
            frame_list.to_float().to_int(self.bits_per_sample))


def __add_dither__(frame_list):
    if (frame_list.bits_per_sample >= 16):
        random_bytes = map(ord, os.urandom((len(frame_list) / 8) + 1))
        white_noise = [(random_bytes[i / 8] & (1 << (i % 8))) >> (i % 8)
                       for i in xrange(len(frame_list))]
    else:
        white_noise = [0] * len(frame_list)

    return pcm.from_list([i ^ w for (i, w) in izip(frame_list,
                                                   white_noise)],
                         frame_list.channels,
                         frame_list.bits_per_sample,
                         True)


class PCMConverter:
    """A PCMReader wrapper for converting attributes.

    For example, this can be used to alter sample_rate, bits_per_sample,
    channel_mask, channel count, or any combination of those
    attributes.  It resamples, downsamples, etc. to achieve the proper
    output.
    """

    def __init__(self, pcmreader,
                 sample_rate,
                 channels,
                 channel_mask,
                 bits_per_sample):
        """Takes a PCMReader input and the attributes of the new stream."""

        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.channel_mask = channel_mask
        self.reader = pcmreader

        self.conversions = []
        if (self.reader.channels != self.channels):
            if (self.channels == 1):
                self.conversions.append(
                    __downmix_to_mono__(pcmreader.channel_mask,
                                        pcmreader.channels))
            elif (self.channels == 2):
                self.conversions.append(
                    __downmixer__(pcmreader.channel_mask,
                                  pcmreader.channels))
            elif (self.channels < pcmreader.channels):
                self.conversions.append(
                    __channel_remover__(pcmreader.channel_mask,
                                        channel_mask))
            elif (self.channels > pcmreader.channels):
                self.conversions.append(
                    __channel_adder__(self.channels))

        if (self.reader.sample_rate != self.sample_rate):
            #if we're converting sample rate and bits-per-sample
            #at the same time, short-circuit the conversion to do both at once
            #which can be sped up somewhat
            if (self.reader.bits_per_sample != self.bits_per_sample):
                self.conversions.append(
                    __convert_sample_rate_and_bits_per_sample__(
                        self.reader.sample_rate,
                        self.sample_rate,
                        self.channels,
                        self.bits_per_sample))
            else:
                self.conversions.append(
                    __convert_sample_rate__(
                        self.reader.sample_rate,
                        self.sample_rate,
                        self.channels,
                        self.bits_per_sample))

        else:
            if (self.reader.bits_per_sample != self.bits_per_sample):
                self.conversions.append(
                    __convert_bits_per_sample__(
                        self.bits_per_sample))

    def read(self, bytes):
        """Try to read a pcm.FrameList of size "bytes"."""

        frame_list = self.reader.read(bytes)

        for converter in self.conversions:
            frame_list = converter.convert(frame_list)

        return frame_list

    def close(self):
        """Closes the stream for reading."""

        self.reader.close()


class ReplayGainReader:
    """A PCMReader which applies ReplayGain on its output."""

    def __init__(self, pcmreader, replaygain, peak):
        """Fields are:

        pcmreader  - a PCMReader object
        replaygain - a floating point dB value
        peak       - the maximum absolute value PCM sample, as a float

        The latter two are typically stored with the file,
        split into album gain and track gain pairs
        which the user can apply based on preference.
        """

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
        """Try to read a pcm.FrameList of size "bytes"."""

        multiplier = self.multiplier
        samples = self.reader.read(bytes)

        if (self.bits_per_sample >= 16):
            random_bytes = map(ord, os.urandom((len(samples) / 8) + 1))
            white_noise = [(random_bytes[i / 8] & (1 << (i % 8))) >> (i % 8)
                           for i in xrange(len(samples))]
        else:
            white_noise = [0] * len(samples)

        return pcm.from_list(
            [(int(round(s * multiplier)) ^ w) for (s, w) in
             izip(samples, white_noise)],
            samples.channels,
            samples.bits_per_sample,
            True)

    def close(self):
        """Closes the stream for reading."""

        self.reader.close()


def applicable_replay_gain(tracks):
    """Returns True if ReplayGain can be applied to a list of AudioFiles.

    This checks their sample rate and channel count to determine
    applicability."""

    sample_rates = set([track.sample_rate() for track in tracks])
    if ((len(sample_rates) > 1) or
        (list(sample_rates)[0] not in (48000,  44100,  32000,  24000, 22050,
                                       16000,  12000,  11025,  8000,
                                       18900,  37800,  56000,  64000,
                                       88200,  96000,  112000, 128000,
                                       144000, 176400, 192000))):
        return False

    channels = set([track.channels() for track in tracks])
    if ((len(channels) > 1) or
        (list(channels)[0] not in (1, 2))):
        return False

    return True


def calculate_replay_gain(tracks):
    """Yields (track,track_gain,track_peak,album_gain,album_peak)
    for each AudioFile in the list of tracks.

    Raises ValueError if a problem occurs during calculation."""

    from . import replaygain as replaygain

    sample_rate = set([track.sample_rate() for track in tracks])
    if (len(sample_rate) != 1):
        raise ValueError(("at least one track is required " +
                          "and all must have the same sample rate"))
    rg = replaygain.ReplayGain(list(sample_rate)[0])
    gains = []
    for track in tracks:
        pcm = track.to_pcm()
        frame = pcm.read(BUFFER_SIZE)
        while (len(frame) > 0):
            rg.update(frame)
            frame = pcm.read(BUFFER_SIZE)
        pcm.close()
        (track_gain, track_peak) = rg.title_gain()
        gains.append((track, track_gain, track_peak))
    (album_gain, album_peak) = rg.album_gain()
    for (track, track_gain, track_peak) in gains:
        yield (track, track_gain, track_peak, album_gain, album_peak)


class InterruptableReader(PCMReader):
    """A PCMReader meant for audio recording.

    It runs read() in a separate thread and stops recording
    when SIGINT is caught.
    """

    def __init__(self, pcmreader, verbose=True):
        """Takes PCMReader object and verbosity flag."""

        #FIXME - update this for Messenger support

        import threading
        import Queue
        import signal

        PCMReader.__init__(self, pcmreader,
                           sample_rate=pcmreader.sample_rate,
                           channels=pcmreader.channels,
                           channel_mask=pcmreader.channel_mask,
                           bits_per_sample=pcmreader.bits_per_sample)

        self.stop_reading = False
        self.data_queue = Queue.Queue()

        self.old_sigint = signal.signal(signal.SIGINT, self.stop)

        thread = threading.Thread(target=self.send_data)
        thread.setDaemon(True)
        thread.start()

        self.verbose = verbose

    def stop(self, *args):
        """The SIGINT signal handler which stops recording."""

        import signal

        self.stop_reading = True
        signal.signal(signal.SIGINT, self.old_sigint)

        if (self.verbose):
            print "Stopping..."

    def send_data(self):
        """The thread for outputting PCM data from reader."""

        #try to use a half second long buffer
        BUFFER_SIZE = self.sample_rate * (self.bits_per_sample / 8) * \
                      self.channels / 2

        s = self.file.read(BUFFER_SIZE)
        while ((len(s) > 0) and (not self.stop_reading)):
            self.data_queue.put(s)
            s = self.file.read(BUFFER_SIZE)

        self.data_queue.put("")

    def read(self, length):
        """Try to read a pcm.FrameList of size "bytes"."""

        return self.data_queue.get()


def ignore_sigint():
    """Sets the SIGINT signal to SIG_IGN.

    Some encoder executables require this in order for
    InterruptableReader to work correctly since we
    want to catch SIGINT ourselves in that case and perform
    a proper shutdown."""

    import signal

    signal.signal(signal.SIGINT, signal.SIG_IGN)


def make_dirs(destination_path):
    """Ensures all directories leading to destination_path are created.

    Raises OSError if a problem occurs during directory creation.
    """

    dirname = os.path.dirname(destination_path)
    if ((dirname != '') and (not os.path.isdir(dirname))):
        os.makedirs(dirname)


#######################
#Generic MetaData
#######################


class MetaData:
    """The base class for storing textual AudioFile metadata.

    This includes things like track name, track number, album name
    and so forth.  It also includes embedded images, if present.

    Fields are stored with the same name they are initialized with.
    Except for images, they can all be manipulated directly
    (images have dedicated set/get/delete methods instead).
    Subclasses are expected to override getattr/setattr
    so that updating attributes will adjust the low-level attributes
    accordingly.
    """

    __FIELDS__ = ("track_name", "track_number", "track_total",
                  "album_name", "artist_name",
                  "performer_name", "composer_name", "conductor_name",
                  "media", "ISRC", "catalog", "copyright",
                  "publisher", "year", "date", "album_number", "album_total",
                  "comment")

    __INTEGER_FIELDS__ = ("track_number", "track_total",
                          "album_number", "album_total")

    def __init__(self,
                 track_name=u"",
                 track_number=0,
                 track_total=0,
                 album_name=u"",
                 artist_name=u"",
                 performer_name=u"",
                 composer_name=u"",
                 conductor_name=u"",
                 media=u"",
                 ISRC=u"",
                 catalog=u"",
                 copyright=u"",
                 publisher=u"",
                 year=u"",
                 date=u"",
                 album_number=0,
                 album_total=0,
                 comment=u"",
                 images=None):
        """Fields are as follows:

        track_name     - the name of this individual track
        track_number   - the number of this track
        track_total    - the total number of tracks
        album_name     - the name of this track's album
        artist_name    - the song's original creator/composer
        performer_name - the song's performing artist
        composer_name  - the song's composer name
        conductor_name - the song's conductor's name
        media          - the album's media type (CD,tape,etc.)
        ISRC           - the song's ISRC
        catalog        - the album's catalog number
        copyright      - the song's copyright information
        publisher      - the song's publisher
        year           - the album's release year
        date           - the original recording date
        album_number   - the disc's volume number, if any
        album_total    - the total number of discs, if any
        comment        - the track's comment string
        images         - a list of Image objects

        track_number, track_total, album_number and album_total are ints.
        images is an optional list of Image objects.
        The rest are unicode strings.
        """

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
        return ("MetaData(%s)" % (
                ",".join(["%s"] * (len(MetaData.__FIELDS__))))) % \
                tuple(["%s=%s" % (field, repr(getattr(self, field)))
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
        return zip(("Title", "Artist", "Performer", "Composer", "Conductor",
                    "Album", "Catalog",
                    "Track Number", "Track Total",
                    "Volume Number", "Volume Total",
                    "ISRC", "Publisher", "Media", "Year", "Date", "Copyright",
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
                            {"length": max_key_length}

            base_comment = unicode(os.linesep.join(
                [_(u"%s Comment:") % (self.__comment_name__())] + \
                [line_template % {"key": key, "value": value} for
                 (key, value) in comment_pairs]))
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
            return set([(getattr(self, attr) == getattr(metadata, attr))
                        for attr in MetaData.__FIELDS__]) == set([True])
        else:
            return False

    def __ne__(self, metadata):
        return not self.__eq__(metadata)

    @classmethod
    def converted(cls, metadata):
        """Converts metadata from another class to this one, if necessary.

        Takes a MetaData-compatible object (or None)
        and returns a new MetaData subclass with the data fields converted
        or None if metadata is None or conversion isn't possible.
        For instance, VorbisComment.converted() returns a VorbisComment
        class.  This way, AudioFiles can offload metadata conversions.
        """

        if (metadata is not None):
            fields = dict([(field, getattr(metadata, field))
                           for field in cls.__FIELDS__])
            fields["images"] = metadata.images()
            return MetaData(**fields)
        else:
            return None

    @classmethod
    def supports_images(cls):
        """Returns True if this MetaData class supports embedded images."""

        return True

    def images(self):
        """Returns a list of embedded Image objects."""

        #must return a copy of our internal array
        #otherwise this will likely not act as expected when deleting
        return self.__images__[:]

    def front_covers(self):
        """Returns a subset of images() which are front covers."""

        return [i for i in self.images() if i.type == 0]

    def back_covers(self):
        """Returns a subset of images() which are back covers."""

        return [i for i in self.images() if i.type == 1]

    def leaflet_pages(self):
        """Returns a subset of images() which are leaflet pages."""

        return [i for i in self.images() if i.type == 2]

    def media_images(self):
        """Returns a subset of images() which are media images."""

        return [i for i in self.images() if i.type == 3]

    def other_images(self):
        """Returns a subset of images() which are other images."""

        return [i for i in self.images() if i.type == 4]

    def add_image(self, image):
        """Embeds an Image object in this metadata.

        Implementations of this method should also affect
        the underlying metadata value
        (e.g. adding a new Image to FlacMetaData should add another
        METADATA_BLOCK_PICTURE block to the metadata).
        """

        if (self.supports_images()):
            self.__images__.append(image)
        else:
            raise ValueError(_(u"This MetaData type does not support images"))

    def delete_image(self, image):
        """Deletes an Image object from this metadata.

        Implementations of this method should also affect
        the underlying metadata value
        (e.g. removing an existing Image from FlacMetaData should
        remove that same METADATA_BLOCK_PICTURE block from the metadata).
        """

        if (self.supports_images()):
            self.__images__.pop(self.__images__.index(image))
        else:
            raise ValueError(_(u"This MetaData type does not support images"))

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values.

        >>> m = MetaData(track_name=u"Track 1",artist_name=u"Artist")
        >>> m2 = MetaData(track_name=u"Track 2",album_name=u"Album")
        >>> m.merge(m2)
        >>> m.track_name
        u'Track 1'
        >>> m.artist_name
        u'Artist'
        >>> m.album_name
        u'Album'

        Subclasses of MetaData should implement this method
        to handle any empty fields their format supports.
        """

        if (metadata is None):
            return

        fields = {}
        for field in self.__FIELDS__:
            if (field not in self.__INTEGER_FIELDS__):
                if (len(getattr(self, field)) == 0):
                    setattr(self, field, getattr(metadata, field))
            else:
                if (getattr(self, field) == 0):
                    setattr(self, field, getattr(metadata, field))

        if ((len(self.images()) == 0) and self.supports_images()):
            for img in metadata.images():
                self.add_image(img)


class AlbumMetaData(dict):
    """A container for several MetaData objects.

    They can be retrieved by track number."""

    def __init__(self, metadata_iter):
        """metadata_iter is an iterator of MetaData objects."""

        dict.__init__(self,
                      dict([(m.track_number, m) for m in metadata_iter]))

    def metadata(self):
        """Returns a single MetaData object of all consistent fields.

        For example, if album_name is the same in all MetaData objects,
        the returned object will have that album_name value.
        If track_name differs, the returned object will not
        have a track_name field.
        """

        return MetaData(**dict([(field, list(items)[0])
                                for (field, items) in
                                [(field,
                                  set([getattr(track, field) for track
                                       in self.values()]))
                                 for field in MetaData.__FIELDS__]
                                if (len(items) == 1)]))


class MetaDataFileException(Exception):
    """A superclass of XMCDException and MBXMLException.

    This allows one to handle any sort of metadata file exception
    consistently."""

    def __unicode__(self):
        return _(u"Invalid XMCD or MusicBrainz XML file")


class AlbumMetaDataFile:
    """A base class for MetaData containing files.

    This includes FreeDB's XMCD files
    and MusicBrainz's XML files."""

    def __init__(self, album_name, artist_name, year, catalog,
                 extra, track_metadata):
        """track_metadata is a list of tuples.  The rest are unicode."""

        self.album_name = album_name
        self.artist_name = artist_name
        self.year = year
        self.catalog = catalog
        self.extra = extra
        self.track_metadata = track_metadata

    def __len__(self):
        return len(self.track_metadata)

    def to_string(self):
        """Returns this object as a plain string of data."""

        raise NotImplementedError()

    @classmethod
    def from_string(cls, string):
        """Given a plain string, returns an object of this class.

        Raises MetaDataFileException if a parsing error occurs."""

        raise NotImplementedError()

    def get_track(self, index):
        """Given a track index (from 0), returns (name, artist, extra).

        name, artist and extra are unicode strings.
        Raises IndexError if out-of-bounds."""

        return self.track_metadata[i]

    def set_track(self, index, name, artist, extra):
        """Sets the track at the given index (from 0) to the given values.

        Raises IndexError if out-of-bounds."""

        self.track_metadata[i] = (name, artist, extra)

    @classmethod
    def from_tracks(cls, tracks):
        """Given a list of AudioFile objects, returns an AlbumMetaDataFile.

        All files are presumed to be from the same album."""

        raise NotImplementedError()

    @classmethod
    def from_cuesheet(cls, cuesheet, total_frames, sample_rate, metadata=None):
        """Returns an AlbumMetaDataFile from a cuesheet.

        This must also include a total_frames and sample_rate integer.
        This works by generating a set of empty tracks and calling
        the from_tracks() method to build a MetaData file with
        the proper placeholders.
        metadata, if present, is applied to all tracks."""

        if (metadata is None):
            metadata = MetaData()

        return cls.from_tracks([DummyAudioFile(
                    length=(pcm_frames * 75) / sample_rate,
                    metadata=metadata,
                    track_number=i + 1) for (i, pcm_frames) in enumerate(
                    cuesheet.pcm_lengths(total_frames))])

    def track_metadata(self, track_number):
        """Given a track_number (from 1), returns a MetaData object.

        Raises IndexError if out-of-bounds or None if track_number is 0."""

        if (track_number == 0):
            return None

        (track_name,
         track_artist,
         track_extra) = self.get_track(track_number - 1)

        if (len(track_artist) == 0):
            track_artist = self.artist_name

        return MetaData(track_name=track_name,
                        track_number=track_number,
                        track_total=len(self),
                        album_name=self.album_name,
                        artist_name=track_artist,
                        catalog=self.catalog,
                        year=self.year)

    def get(self, track_index, default):
        try:
            return self.track_metadata(track_index)
        except IndexError:
            return default

    def track_metadatas(self):
        """Iterates over all the MetaData objects in this file."""

        for i in xrange(len(self)):
            yield self.track_metadata(i + 1)

    def metadata(self):
        """Returns a single MetaData object of all consistent fields.

        For example, if album_name is the same in all MetaData objects,
        the returned object will have that album_name value.
        If track_name differs, the returned object will not
        have a track_name field.
        """

        return MetaData(**dict([(field, list(items)[0])
                                for (field, items) in
                                [(field,
                                  set([getattr(track, field) for track
                                       in self.track_metadatas()]))
                                 for field in MetaData.__FIELDS__]
                                if (len(items) == 1)]))

#######################
#Image MetaData
#######################


class Image:
    """An image data container."""

    def __init__(self, data, mime_type, width, height,
                 color_depth, color_count, description, type):
        """Fields are as follows:

        data        - plain string of the actual binary image data
        mime_type   - unicode string of the image's MIME type
        width       - width of image, as integer number of pixels
        height      - height of image, as integer number of pixels
        color_depth - color depth of image (24 for JPEG, 8 for GIF, etc.)
        color_count - number of palette colors, or 0
        description - a unicode string
        type - an integer type whose values are:
               0 - front cover
               1 - back cover
               2 - leaflet page
               3 - media
               4 - other
        """

        self.data = data
        self.mime_type = mime_type
        self.width = width
        self.height = height
        self.color_depth = color_depth
        self.color_count = color_count
        self.description = description
        self.type = type

    def suffix(self):
        """Returns the image's recommended suffix as a plain string.

        For example, an image with mime_type "image/jpeg" return "jpg".
        """

        return {"image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/gif": "gif",
                "image/png": "png",
                "image/x-ms-bmp": "bmp",
                "image/tiff": "tiff"}.get(self.mime_type, "bin")

    def type_string(self):
        """Returns the image's type as a human readable plain string.

        For example, an image of type 0 returns "Front Cover".
        """

        return {0: "Front Cover",
                1: "Back Cover",
                2: "Leaflet Page",
                3: "Media",
                4: "Other"}.get(self.type, "Other")

    def __repr__(self):
        return ("Image(mime_type=%s,width=%s,height=%s,color_depth=%s," +
                "color_count=%s,description=%s,type=%s,...)") % \
                (repr(self.mime_type), repr(self.width), repr(self.height),
                 repr(self.color_depth), repr(self.color_count),
                 repr(self.description), repr(self.type))

    def __unicode__(self):
        return u"Picture : %s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width, self.height, self.mime_type)

    @classmethod
    def new(cls, image_data, description, type):
        """Builds a new Image object from raw data.

        image_data is a plain string of binary image data.
        description is a unicode string.
        type as an image type integer.

        The width, height, color_depth and color_count fields
        are determined by parsing the binary image data.
        Raises InvalidImage if some error occurs during parsing.
        """

        img = image_metrics(image_data)

        return Image(data=image_data,
                     mime_type=img.mime_type,
                     width=img.width,
                     height=img.height,
                     color_depth=img.bits_per_pixel,
                     color_count=img.color_count,
                     description=description,
                     type=type)

    def thumbnail(self, width, height, format):
        """Returns a new Image object with the given attributes.

        width and height are integers.
        format is a string such as "JPEG".
        """

        return Image.new(thumbnail_image(self.data, width, height, format),
                         self.description, self.type)

    def __eq__(self, image):
        if (image is not None):
            return set([(getattr(self, attr) == getattr(image, attr))
                        for attr in
                        ("data", "mime_type", "width", "height",
                         "color_depth", "color_count", "description",
                         "type")]) == set([True])
        else:
            return False

    def __ne__(self, image):
        return not self.__eq__(image)

#######################
#ReplayGain Metadata
#######################


class ReplayGain:
    """A container for ReplayGain data."""

    def __init__(self, track_gain, track_peak, album_gain, album_peak):
        """Values are:

        track_gain - a dB float value
        track_peak - the highest absolute value PCM sample, as a float
        album_gain - a dB float value
        album_peak - the highest absolute value PCM sample, as a float

        They are also attributes.
        """

        self.track_gain = float(track_gain)
        self.track_peak = float(track_peak)
        self.album_gain = float(album_gain)
        self.album_peak = float(album_peak)

    def __repr__(self):
        return "ReplayGain(%s,%s,%s,%s)" % \
            (self.track_gain, self.track_peak,
             self.album_gain, self.album_peak)

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

class UnsupportedTracknameField(Exception):
    """Raised by AudioFile.track_name()
    if its format string contains unknown fields."""

    def __init__(self, field):
        self.field = field

    def error_msg(self, messenger):
        messenger.error(_(u"Unknown field \"%s\" in file format") % \
                            (self.field))
        messenger.info(_(u"Supported fields are:"))
        for field in sorted(MetaData.__FIELDS__ + \
                            ("album_track_number", "suffix")):
            if (field == 'track_number'):
                messenger.info(u"%(track_number)2.2d")
            else:
                messenger.info(u"%%(%s)s" % (field))

        messenger.info(u"%(basename)s")


class AudioFile:
    """An abstract class representing audio files on disk.

    This class should be extended to handle different audio
    file formats."""

    SUFFIX = ""
    NAME = ""
    DEFAULT_COMPRESSION = ""
    COMPRESSION_MODES = ("",)
    COMPRESSION_DESCRIPTIONS = {}
    BINARIES = tuple()
    REPLAYGAIN_BINARIES = tuple()

    def __init__(self, filename):
        """filename is a plain string.

        Raises InvalidFile or subclass if the file is invalid in some way."""

        self.filename = filename

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        return False

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        raise NotImplementedError()

    def channels(self):
        """Returns an integer number of channels this track contains."""

        raise NotImplementedError()

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        #WARNING - This only returns valid masks for 1 and 2 channel audio
        #anything over 2 channels raises a ValueError
        #since there isn't any standard on what those channels should be.
        #AudioFiles that support more than 2 channels should override
        #this method with one that returns the proper mask.
        return ChannelMask.from_channels(self.channels())

    def lossless(self):
        """Returns True if this track's data is stored losslessly."""

        raise NotImplementedError()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        pass

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        return None

    def delete_metadata(self):
        """Deletes the track's MetaData.

        This removes or unsets tags as necessary in order to remove all data.
        Raises IOError if unable to write the file."""

        pass

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        raise NotImplementedError()

    def cd_frames(self):
        """Returns the total length of the track in CD frames.

        Each CD frame is 1/75th of a second."""

        try:
            return (self.total_frames() * 75) / self.sample_rate()
        except ZeroDivisionError:
            return 0

    def seconds_length(self):
        """Returns the length of the track as a Decimal number of seconds."""

        import decimal

        try:
            return (decimal.Decimal(self.total_frames()) /
                    decimal.Decimal(self.sample_rate()))
        except decimal.DivisionByZero:
            return decimal.Decimal(0)

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        raise NotImplementedError()

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data.

        If an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message."""

        #if a subclass implements to_wave(),
        #this doesn't need to be implemented
        #if a subclass implements to_pcm(),
        #to_wave() doesn't need to be implemented
        #or, one can implement both

        raise NotImplementedError()

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AudioFile-compatible object.

        For example, to encode the FlacAudio file "file.flac" from "file.wav"
        at compression level "5":

        >>> flac = FlacAudio.from_pcm("file.flac",
        ...                           WaveAudio("file.wav").to_pcm(),
        ...                           "5")

        May raise EncodingError if some problem occurs when
        encoding the input file.  This includes an error
        in the input stream, a problem writing the output file,
        or even an EncodingError subclass such as
        "UnsupportedBitsPerSample" if the input stream
        is formatted in a way this class is unable to support.
        """

        raise NotImplementedError()

    def convert(self, target_path, target_class, compression=None):
        """Encodes a new AudioFile from existing AudioFile.

        Take a filename string, target class and optional compression string.
        Encodes a new AudioFile in the target class and returns
        the resulting object.
        May raise EncodingError if some problem occurs during encoding."""

        return target_class.from_pcm(target_path,
                                     self.to_pcm(),
                                     compression)

    @classmethod
    def __unlink__(cls, filename):
        try:
            os.unlink(filename)
        except OSError:
            pass

    def track_number(self):
        """Returns this track's number as an integer.

        This first checks MetaData and then makes a guess from the filename.
        If neither yields a good result, returns 0."""

        metadata = self.get_metadata()
        if ((metadata is not None) and (metadata.track_number > 0)):
            return metadata.track_number
        else:
            try:
                return int(re.findall(
                        r'\d{2,3}',
                        os.path.basename(self.filename))[0]) % 100
            except IndexError:
                return 0

    def album_number(self):
        """Returns this track's album number as an integer.

        This first checks MetaData and then makes a guess from the filename.
        If neither yields a good result, returns 0."""

        metadata = self.get_metadata()
        if ((metadata is not None) and (metadata.album_number > 0)):
            return metadata.album_number
        elif ((metadata is not None) and (metadata.track_number > 0)):
            return 0
        else:
            try:
                long_track_number = int(re.findall(
                        r'\d{3}',
                        os.path.basename(self.filename))[0])
                return long_track_number / 100
            except IndexError:
                return 0

    @classmethod
    def track_name(cls, file_path, track_metadata=None, format=None,
                   suffix=None):
        """Constructs a new filename string.

        Given a plain string to an existing path,
        a MetaData-compatible object (or None),
        a UTF-8-encoded Python format string
        and an ASCII-encoded suffix string (such as "mp3")
        returns a plain string of a new filename with format's
        fields filled-in and encoded as FS_ENCODING.
        Raises UnsupportedTracknameField if the format string
        contains invalid template fields."""

        if (format is None):
            format = FILENAME_FORMAT
        if (suffix is None):
            suffix = cls.SUFFIX
        try:
            #prefer a track number from MetaData, if available
            if ((track_metadata is not None) and
                (track_metadata.track_number > 0)):
                track_number = track_metadata.track_number
            else:
                try:
                    track_number = int(re.findall(
                            r'\d{2,4}',
                            os.path.basename(file_path))[0]) % 100
                except IndexError:
                    track_number = 0

            #prefer an album_number from MetaData, if available
            if ((track_metadata is not None) and
                (track_metadata.album_number > 0)):
                album_number = track_metadata.album_number
            else:
                try:
                    album_number = int(re.findall(
                            r'\d{2,4}',
                            os.path.basename(file_path))[0]) / 100
                except IndexError:
                    album_number = 0

            if (track_metadata is not None):
                track_total = track_metadata.track_total
                album_total = track_metadata.album_total
            else:
                track_total = 0
                album_total = 0

            format_dict = {u"track_number": track_number,
                           u"album_number": album_number,
                           u"track_total": track_total,
                           u"album_total": album_total,
                           u"suffix": suffix.decode('ascii')}

            if (album_number == 0):
                format_dict[u"album_track_number"] = u"%2.2d" % (track_number)
            else:
                album_digits = len(str(album_total))

                format_dict[u"album_track_number"] = (
                    u"%%%(album_digits)d.%(album_digits)dd%%2.2d" %
                    {"album_digits": album_digits} %
                    (album_number, track_number))

            if (track_metadata is not None):
                for field in track_metadata.__FIELDS__:
                    if ((field != "suffix") and
                        (field not in MetaData.__INTEGER_FIELDS__)):
                        format_dict[field.decode('ascii')] = getattr(
                            track_metadata,
                            field).replace(u'/', u'-').replace(unichr(0), u' ')
            else:
                for field in MetaData.__FIELDS__:
                    if (field not in MetaData.__INTEGER_FIELDS__):
                        format_dict[field.decode('ascii')] = u""

            format_dict[u"basename"] = os.path.splitext(
                os.path.basename(file_path))[0].decode(FS_ENCODING,
                                                       'replace')

            return (format.decode('utf-8', 'replace') % format_dict).encode(
                FS_ENCODING, 'replace')
        except KeyError, error:
            raise UnsupportedTracknameField(unicode(error.args[0]))

    @classmethod
    def add_replay_gain(cls, filenames):
        """Adds ReplayGain values to a list of filename strings.

        All the filenames must be of this AudioFile type.
        Raises ValueError if some problem occurs during ReplayGain application.
        """

        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track, cls)]

    @classmethod
    def can_add_replay_gain(cls):
        """Returns True if we have the necessary binaries to add ReplayGain."""

        return False

    @classmethod
    def lossless_replay_gain(cls):
        """Returns True of applying ReplayGain is a lossless process.

        For example, if it is applied by adding metadata tags
        rather than altering the file's data itself."""

        return True

    def replay_gain(self):
        """Returns a ReplayGain object of our ReplayGain values.

        Returns None if we have no values.
        Note that if applying ReplayGain is a lossy process,
        this will typically also return None."""

        return None

    def set_cuesheet(self, cuesheet):
        """Imports cuesheet data from a Cuesheet-compatible object.

        This are objects with catalog(), ISRCs(), indexes(), and pcm_lengths()
        methods.  Raises IOError if an error occurs setting the cuesheet."""

        pass

    def get_cuesheet(self):
        """Returns the embedded Cuesheet-compatible object, or None.

        Raises IOError if a problem occurs when reading the file."""

        return None

    def __eq__(self, audiofile):
        if (isinstance(audiofile, AudioFile)):
            p1 = self.to_pcm()
            p2 = audiofile.to_pcm()
            try:
                return pcm_cmp(p1, p2)
            finally:
                p1.close()
                p2.close()
        else:
            return False

    def __ne__(self, audiofile):
        return not self.__eq__(audiofile)

    def verify(self):
        """Verifies the current file for correctness.

        Returns True if the file is okay.
        Raises an InvalidFile with an error message if there is
        some problem with the file."""

        decoder = self.to_pcm()
        pcm_frame_count = 0
        try:
            framelist = decoder.read(BUFFER_SIZE)
            while (len(framelist) > 0):
                pcm_frame_count += framelist.frames
                framelist = decoder.read(BUFFER_SIZE)
        except (IOError, ValueError), err:
            raise InvalidFile(str(err))

        try:
            decoder.close()
        except DecodingError, err:
            raise InvalidFile(err.error_message)

        if (pcm_frame_count == self.total_frames()):
            return True
        else:
            raise InvalidFile("incorrect PCM frame count")

    @classmethod
    def has_binaries(cls, system_binaries):
        """Returns True if all the required binaries can be found.

        Checks the __system_binaries__ class for which path to check."""

        return set([True] + \
                   [system_binaries.can_execute(system_binaries[command])
                    for command in cls.BINARIES]) == set([True])

class WaveContainer(AudioFile):
    """An audio type which supports storing foreign RIFF chunks.

    These chunks must be preserved during a round-trip:

    >>> WaveContainer("file", "input.wav").to_wave("output.wav")
    """

    def to_wave(self, wave_filename):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        pcmreader = self.to_pcm()
        WaveAudio.from_pcm(wave_filename, pcmreader)
        pcmreader.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new AudioFile compatible object.

        For example, to encode FlacAudio file "flac.flac" from "file.wav"
        at compression level "5":

        >>> flac = FlacAudio.from_wave("file.flac","file.wav","5")
        """

        return cls.from_pcm(filename,
                            WaveAudio(wave_filename).to_pcm(),
                            compression)

    def has_foreign_riff_chunks(self):
        """Returns True if the audio file contains non-audio RIFF chunks.

        During transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks."""

        return False

    def convert(self, target_path, target_class, compression=None):
        """Encodes a new AudioFile from existing AudioFile.

        Take a filename string, target class and optional compression string.
        Encodes a new AudioFile in the target class and returns
        the resulting object.
        May raise EncodingError if some problem occurs during encoding."""

        import tempfile

        if (target_class == WaveAudio):
            self.to_wave(target_path)
            return WaveAudio(target_path)
        elif (self.has_foreign_riff_chunks() and
              hasattr(target_class, "from_wave")):
            temp_wave = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                self.to_wave(temp_wave.name)
                return target_class.from_wave(target_path,
                                              temp_wave.name,
                                              compression)
            finally:
                temp_wave.close()
        else:
            return target_class.from_pcm(target_path,
                                         self.to_pcm(),
                                         compression)

class AiffContainer(AudioFile):
    """An audio type which supports storing foreign AIFF chunks.

    These chunks must be preserved during a round-trip:

    >>> AiffContainer("file", "input.aiff").to_aiff("output.aiff")
    """

    def to_aiff(self, aiff_filename):
        """Writes the contents of this file to the given .aiff filename string.

        Raises EncodingError if some error occurs during decoding."""

        pcmreader = self.to_pcm()
        AiffAudio.from_pcm(wave_filename, pcmreader)
        pcmreader.close()

    @classmethod
    def from_aiff(cls, filename, aiff_filename, compression=None):
        """Encodes a new AudioFile from an existing .aiff file.

        Takes a filename string, aiff_filename string
        of an existing AiffAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new AudioFile compatible object.

        For example, to encode FlacAudio file "flac.flac" from "file.aiff"
        at compression level "5":

        >>> flac = FlacAudio.from_wave("file.flac","file.aiff","5")
        """

        return cls.from_pcm(filename,
                            AiffAudio(wave_filename).to_pcm(),
                            compression)

    def has_foreign_aiff_chunks(self):
        """Returns True if the audio file contains non-audio AIFF chunks.

        During transcoding, if the source audio file has foreign AIFF chunks
        and the target audio format supports foreign AIFF chunks,
        conversion should be routed through .aiff conversion
        to avoid losing those chunks."""

        return False

    def convert(self, target_path, target_class, compression=None):
        """Encodes a new AudioFile from existing AudioFile.

        Take a filename string, target class and optional compression string.
        Encodes a new AudioFile in the target class and returns
        the resulting object.
        May raise EncodingError if some problem occurs during encoding."""

        if (target_class == AiffAudio):
            self.to_aiff(target_path)
            return AiffAudio(target_path)
        elif (self.has_foreign_aiff_chunks() and
              hasattr(target_class, "from_aiff")):
            temp_aiff = tempfile.NamedTemporaryFile(suffix=".aiff")
            try:
                self.to_aiff(temp_aiff.name)
                return target_class.from_aiff(target_path,
                                              temp_aiff.name,
                                              compression)
            finally:
                temp_aiff.close()
        else:
            return target_class.from_pcm(target_path,
                                         self.to_pcm(),
                                         compression)

class DummyAudioFile(AudioFile):
    """A placeholder AudioFile object with external data."""

    def __init__(self, length, metadata, track_number=0):
        """Fields are as follows:

        length       - the dummy track's length, in CD frames
        metadata     - a MetaData object
        track_number - the track's number on CD, starting from 1
        """

        self.__length__ = length
        self.__metadata__ = metadata
        self.__track_number__ = track_number

        AudioFile.__init__(self, "")

    def get_metadata(self):
        """Returns a MetaData object, or None."""

        return self.__metadata__

    def cd_frames(self):
        """Returns the total length of the track in CD frames.

        Each CD frame is 1/75th of a second."""

        return self.__length__

    def track_number(self):
        """Returns this track's number as an integer."""

        return self.__track_number__

    def sample_rate(self):
        """Returns 44100."""

        return 44100

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return (self.cd_frames() * self.sample_rate()) / 75

###########################
#Cuesheet/TOC file handling
###########################

#Cuesheets and TOC files are bundled into a unified Sheet interface


class SheetException(ValueError):
    """A parent exception for CueException and TOCException."""

    pass


def read_sheet(filename):
    """Returns a TOCFile or Cuesheet object from filename.

    May raise a SheetException if the file cannot be parsed correctly."""

    import toc
    import cue

    try:
        #try TOC first, since its CD_DA header makes it easier to spot
        return toc.read_tocfile(filename)
    except SheetException:
        return cue.read_cuesheet(filename)


def parse_timestamp(s):
    """Parses a timestamp string into an integer.

    This presumes the stamp is stored: "hours:minutes:frames"
    where each CD frame is 1/75th of a second.
    Or, if the stamp is a plain integer, it is returned directly.
    This does no error checking.  Presumably a regex will ensure
    the stamp is formatted correctly before parsing it to an int.
    """

    if (":" in s):
        (m, s, f) = map(int, s.split(":"))
        return (m * 60 * 75) + (s * 75) + f
    else:
        return int(s)


def build_timestamp(i):
    """Returns a timestamp string from an integer number of CD frames.

    Each CD frame is 1/75th of a second.
    """

    return "%2.2d:%2.2d:%2.2d" % ((i / 75) / 60, (i / 75) % 60, i % 75)


def sheet_to_unicode(sheet, total_frames):
    """Returns formatted unicode from a cuesheet object and total PCM frames.

    Its output is pretty-printed for eventual display by trackinfo.
    """

    #FIXME? - This (and pcm_lengths() in general) assumes all cuesheets
    #have a sample rate of 44100Hz.
    #It's difficult to envision a scenario
    #in which this assumption doesn't hold
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
              (" (ISRC %s)" % (ISRCs[i + 1].decode('ascii', 'replace'))) if
                ((i + 1) in ISRCs.keys()) else u"")
         for (i, length) in enumerate(sheet.pcm_lengths(total_frames))])

    if ((sheet.catalog() is not None) and
        (len(sheet.catalog()) > 0)):
        return u"  Catalog - %s%s%s" % \
            (sheet.catalog().decode('ascii', 'replace'),
             os.linesep, tracks)
    else:
        return tracks


def at_a_time(total, per):
    """Yields "per" integers from "total" until exhausted.

    For example:
    >>> list(at_a_time(10, 3))
    [3, 3, 3, 1]
    """

    for i in xrange(total / per):
        yield per
    yield total % per


from __image__ import *

from __wav__ import *

from __au__ import *
from __vorbiscomment__ import *
from __id3__ import *
from __aiff__ import *
from __flac__ import *

from __ape__ import *
from __mp3__ import *
from __vorbis__ import *
from __m4a__ import *
from __wavpack__ import *
from __musepack__ import *
from __speex__ import *
from __shn__ import *

from __dvda__ import *


#######################
#CD data
#######################

#keep in mind the whole of CD reading isn't remotely thread-safe
#due to the linear nature of CD access,
#reading from more than one track of a given CD at the same time
#is something code should avoid at all costs!
#there's simply no way to accomplish that cleanly

class CDDA:
    """A CDDA device which contains CDTrackReader objects."""

    def __init__(self, device_name, speed=None, perform_logging=True):
        """device_name is a string, speed is an optional int."""

        import cdio

        cdrom_type = cdio.identify_cdrom(device_name)
        if (cdrom_type & cdio.CD_IMAGE):
            self.cdda = cdio.CDImage(device_name, cdrom_type)
            self.perform_logging = False
        else:
            self.cdda = cdio.CDDA(device_name)
            if (speed is not None):
                self.cdda.set_speed(speed)
            self.perform_logging = perform_logging

        self.total_tracks = len([track_type for track_type in
                                 map(self.cdda.track_type,
                                     xrange(1, self.cdda.total_tracks() + 1))
                                 if (track_type == 0)])

    def __len__(self):
        return self.total_tracks

    def __getitem__(self, key):
        if ((key < 1) or (key > self.total_tracks)):
            raise IndexError(key)
        else:
            try:
                sample_offset = int(config.get_default("System",
                                                       "cdrom_read_offset",
                                                       "0"))
            except ValueError:
                sample_offset = 0

            reader = CDTrackReader(self.cdda, int(key), self.perform_logging)

            if (sample_offset == 0):
                return reader
            elif (sample_offset > 0):
                import math

                pcm_frames = reader.length() * 588

                #adjust start and end sectors to account for the offset
                reader.start += (sample_offset / 588)
                reader.end += int(math.ceil(sample_offset / 588.0))
                reader.end = min(reader.end, self.last_sector())

                #then wrap the reader in a window to fine-tune the offset
                reader = PCMReaderWindow(reader, sample_offset, pcm_frames)
                reader.track_number = reader.pcmreader.track_number
                reader.rip_log = reader.pcmreader.rip_log
                reader.length = reader.pcmreader.length
                reader.offset = reader.pcmreader.offset
                return reader
            elif (sample_offset < 0):
                import math

                pcm_frames = reader.length() * 588

                #adjust start and end sectors to account for the offset
                reader.start += sample_offset / 588
                reader.end += int(math.ceil(sample_offset / 588.0))

                #then wrap the reader in a window to fine-tune the offset
                if (reader.start >= self.first_sector()):
                    reader = PCMReaderWindow(
                        reader,
                        sample_offset + (-(sample_offset / 588) * 588),
                        pcm_frames)
                else:
                    reader.start = self.first_sector()
                    reader = PCMReaderWindow(reader, sample_offset, pcm_frames)
                reader.track_number = reader.pcmreader.track_number
                reader.rip_log = reader.pcmreader.rip_log
                reader.length = reader.pcmreader.length
                reader.offset = reader.pcmreader.offset
                return reader

    def __iter__(self):
        for i in range(1, self.total_tracks + 1):
            yield self[i]

    def length(self):
        """Returns the length of the CD in CD frames."""

        #lead-in should always be 150
        return self.last_sector() + 150 + 1

    def close(self):
        """Closes the CDDA device."""

        pass

    def first_sector(self):
        """Returns the first sector's location, in CD frames."""

        return self.cdda.first_sector()

    def last_sector(self):
        """Returns the last sector's location, in CD frames."""

        return self.cdda.last_sector()


class PCMReaderWindow:
    """A class for cropping a PCMReader to a specific window of frames"""

    def __init__(self, pcmreader, initial_offset, pcm_frames):
        """initial_offset is how many frames to crop, and may be negative
        pcm_frames is the total length of the window

        If the window is outside the PCMReader's data
        (that is, initial_offset is negative, or
        pcm_frames is longer than the total stream)
        those samples are padded with 0s."""

        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample

        self.initial_offset = initial_offset
        self.pcm_frames = pcm_frames

    def read(self, bytes):
        if (self.pcm_frames > 0):
            if (self.initial_offset == 0):
                #once the initial offset is accounted for,
                #read a framelist from the pcmreader

                framelist = self.pcmreader.read(bytes)
                if (framelist.frames <= self.pcm_frames):
                    if (framelist.frames > 0):
                        #return framelist if it has data
                        #and is smaller than remaining frames
                        self.pcm_frames -= framelist.frames
                        return framelist
                    else:
                        #otherwise, pad remaining data with 0s
                        framelist = pcm.from_list([0] *
                                                  (self.pcm_frames) *
                                                  self.channels,
                                                  self.channels,
                                                  self.bits_per_sample,
                                                  True)
                        self.pcm_frames = 0
                        return framelist
                else:
                    #crop framelist to be smaller
                    #if its data is larger than what remains to be read
                    framelist = framelist.split(self.pcm_frames)[0]
                    self.pcm_frames = 0
                    return framelist

            elif (self.initial_offset > 0):
                #remove frames if initial offset is positive

                #if initial_offset is large, read as many framelists as needed
                framelist = self.pcmreader.read(bytes)
                while (self.initial_offset > framelist.frames):
                    self.initial_offset -= framelist.frames
                    framelist = self.pcmreader.read(bytes)

                (removed, framelist) = framelist.split(self.initial_offset)
                self.initial_offset -= removed.frames
                if (framelist.frames > 0):
                    self.pcm_frames -= framelist.frames
                    return framelist
                else:
                    #if the entire framelist is cropped,
                    #return another one entirely
                    return self.read(bytes)
            elif (self.initial_offset < 0):
                #pad framelist with 0s if initial offset is negative
                framelist = pcm.from_list([0] *
                                          (-self.initial_offset) *
                                          self.channels,
                                          self.channels,
                                          self.bits_per_sample,
                                          True)
                self.initial_offset = 0
                self.pcm_frames -= framelist.frames
                return framelist
        else:
            #once all frames have been sent, return empty framelists
            return pcm.FrameList("", self.channels, self.bits_per_sample,
                                 False, True)

    def close(self):
        self.pcmreader.close()


class CDTrackLog(dict):
    """A container for CD reading log information, implemented as a dict."""

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
        return ", ".join(["%%(%s)d %s" % (field, field)
                          for field in
                          ("rderr", "skip", "atom", "edge",
                           "drop", "dup", "drift")]) % \
                           {"edge": self.get(2, 0),
                            "atom": self.get(3, 0),
                            "skip": self.get(6, 0),
                            "drift": self.get(7, 0),
                            "drop": self.get(10, 0),
                            "dup": self.get(11, 0),
                            "rderr": self.get(12, 0)}


class CDTrackReader(PCMReader):
    """A PCMReader-compatible object which reads from CDDA."""

    def __init__(self, cdda, track_number, perform_logging=True):
        """cdda is a cdio.CDDA object.  track_number is offset from 1."""

        PCMReader.__init__(
            self, None,
            sample_rate=44100,
            channels=2,
            channel_mask=int(ChannelMask.from_fields(front_left=True,
                                                     front_right=True)),
            bits_per_sample=16)

        self.cdda = cdda
        self.track_number = track_number

        (self.start, self.end) = cdda.track_offsets(track_number)

        self.position = self.start
        self.cursor_placed = False

        self.perform_logging = perform_logging
        self.rip_log = CDTrackLog()

    def offset(self):
        """Returns this track's CD offset, in CD frames."""

        return self.start + 150

    def length(self):
        """Returns this track's length, in CD frames."""

        return self.end - self.start + 1

    def log(self, i, v):
        """Adds a log entry to the track's rip_log.

        This is meant to be called from CD reading callbacks."""

        if v in self.rip_log:
            self.rip_log[v] += 1
        else:
            self.rip_log[v] = 1

    def __read_sectors__(self, sectors):
        #if we haven't moved CDDA to the track start yet, do it now
        if (not self.cursor_placed):
            self.cdda.seek(self.start)
            if (self.perform_logging):
                cdio.set_read_callback(self.log)

            self.position = self.start
            self.cursor_placed = True

        if (self.position <= self.end):
            s = self.cdda.read_sectors(min(
                    sectors, self.end - self.position + 1))
            self.position += sectors
            return s
        else:
            return pcm.from_list([], 2, 16, True)

    def read(self, bytes):
        """Try to read a pcm.FrameList of size "bytes".

        For CD reading, this will be a sector-aligned number."""

        #returns a sector-aligned number of bytes
        #(divisible by 2352 bytes, basically)
        #or at least 1 sector's worth, if "bytes" is too small
        return self.__read_sectors__(max(bytes / 2352, 1))

    def close(self):
        """Closes the CD track for reading."""

        self.position = self.start
        self.cursor_placed = False


#returns the value in item_list which occurs most often
def __most_numerous__(item_list):
    counts = {}

    if (len(item_list) == 0):
        return ""

    for item in item_list:
        counts.setdefault(item, []).append(item)

    return sorted([(item, len(counts[item])) for item in counts.keys()],
                  lambda x, y: cmp(x[1], y[1]))[-1][0]


from __freedb__ import *
from __musicbrainz__ import *


def read_metadata_file(filename):
    """Returns an AlbumMetaDataFile-compatible file from a filename string.

    Raises a MetaDataFileException exception if an error occurs
    during reading.
    """

    try:
        data = file(filename, 'rb').read()
    except IOError, msg:
        raise MetaDataFileException(str(msg))

    #try XMCD first
    try:
        return XMCD.from_string(data)
    except XMCDException:
        pass

    #then try MusicBrainz
    try:
        return MusicBrainzReleaseXML.from_string(data)
    except MBXMLException:
        pass

    #otherwise, throw exception
    raise MetaDataFileException(filename)


def analyze_frames(pcmreader):
    """Iterates over a PCMReader's analyze_frame() results."""

    frame = pcmreader.analyze_frame()
    while (frame is not None):
        yield frame
        frame = pcmreader.analyze_frame()
    pcmreader.close()


#######################
#Multiple Jobs Handling
#######################


class ExecQueue:
    """A class for running multiple jobs in parallel."""

    def __init__(self):
        self.todo = []
        self.return_values = set([])

    def execute(self, function, args, kwargs=None):
        """Queues the given function with argument list and kwargs dict."""

        self.todo.append((function, args, kwargs))

    def __run__(self, function, args, kwargs):
        pid = os.fork()
        if (pid > 0):  # parent
            return pid
        else:          # child
            if (kwargs is not None):
                function(*args, **kwargs)
            else:
                function(*args)
            sys.exit(0)

    def run(self, max_processes=1):
        """Performs the queued functions in separate subprocesses.

        This runs "max_processes" number of functions at a time.
        It works by spawning a new child process for each function,
        executing it and spawning a new child as each one exits.
        Therefore, any side effects beyond altering files on
        disk do not propogate back to the parent."""

        max_processes = max(max_processes, 1)

        process_pool = set([])

        #fill the process_pool to the limit
        while ((len(self.todo) > 0) and (len(process_pool) < max_processes)):
            (function, args, kwargs) = self.todo.pop(0)
            process_pool.add(self.__run__(function, args, kwargs))
            #print "Filling %s" % (repr(process_pool))

        #as processes end, keep adding new ones to the pool
        #until we run out of queued jobs

        while (len(self.todo) > 0):
            try:
                (pid, return_value) = os.waitpid(0, 0)
                process_pool.remove(pid)
                self.return_values.add(return_value)
                (function, args, kwargs) = self.todo.pop(0)
                process_pool.add(self.__run__(function, args, kwargs))
                #print "Resuming %s" % (repr(process_pool))
            except KeyError:
                continue

        #finally, wait for the running jobs to finish
        while (len(process_pool) > 0):
            try:
                (pid, return_value) = os.waitpid(0, 0)
                process_pool.remove(pid)
                self.return_values.add(return_value)
                #print "Emptying %s" % (repr(process_pool))
            except KeyError:
                continue

class ExecQueue2:
    """A class for running multiple jobs and accumulating results."""

    def __init__(self):
        self.todo = []
        self.return_values = set([])

        #a dict of reader->pid values as returned by __run__()
        self.process_pool = {}

    def execute(self, function, args, kwargs=None):

        self.todo.append((function, args, kwargs))

    def __run__(self, function, args, kwargs):
        """executes the given function and arguments in a child job

        returns a (pid, reader) tuple where pid is an int of the child job
        and reader is a file object containing its piped data"""

        import cPickle

        (pipe_read, pipe_write) = os.pipe()
        pid = os.fork()
        if (pid > 0):  #parent
            os.close(pipe_write)
            reader = os.fdopen(pipe_read, 'r')
            return (pid, reader)
        else:          #child
            os.close(pipe_read)
            writer = os.fdopen(pipe_write, 'w')
            if (kwargs is not None):
                cPickle.dump(function(*args, **kwargs), writer)
            else:
                cPickle.dump(function(*args), writer)
            sys.exit(0)

    def __add_job__(self):
        """removes a queued function and adds it to our running pool"""

        (function, args, kwargs) = self.todo.pop(0)
        (pid, file_pointer) = self.__run__(function, args, kwargs)
        self.process_pool[file_pointer] = pid

    def __await_jobs__(self):
        """yields a reader file object per finished job

        If the child job exited properly, that reader will have
        the pickled contents of the completed Python function
        and it can be used to find the child's PID to be waited for
        via the process pool.
        In addition, the returned values of finished child processes
        are added to our "return_values" attribute."""

        import select
        import cPickle

        (readable,
         writeable,
         exceptional) = select.select(list(self.process_pool.keys()), [], [])
        for reader in readable:
            try:
                result = cPickle.load(reader)
            except EOFError:
                result = None
            (pid, return_value) = os.waitpid(self.process_pool[reader], 0)
            self.return_values.add(return_value)
            yield (reader, result)

    def run(self, max_processes=1):
        """execute all queued functions

        Yields the result of each executed function as they complete."""

        max_processes = max(max_processes, 1)

        #fill the process pool to the limit
        while ((len(self.todo) > 0) and
               (len(self.process_pool) < max_processes)):
            self.__add_job__()

        #as processes end, keep adding new ones to the pool
        #until we run out of queued jobs
        while (len(self.todo) > 0):
            for (reader, result) in self.__await_jobs__():
                del(self.process_pool[reader])
                if (len(self.todo) > 0):
                    self.__add_job__()
                yield result

        #finally, wait for the running jobs to finish
        while (len(self.process_pool) > 0):
            for (reader, result) in self.__await_jobs__():
                del(self.process_pool[reader])
            yield result


#***ApeAudio temporarily removed***
#Without a legal alternative to mac-port, I shall have to re-implement
#Monkey's Audio with my own code in order to make it available again.
#Yet another reason to avoid that unpleasant file format...

AVAILABLE_TYPES = (FlacAudio,
                   OggFlacAudio,
                   MP3Audio,
                   MP2Audio,
                   WaveAudio,
                   VorbisAudio,
                   SpeexAudio,
                   AiffAudio,
                   AuAudio,
                   M4AAudio,
                   AACAudio,
                   ALACAudio,
                   WavPackAudio,
                   ShortenAudio)

TYPE_MAP = dict([(track_type.NAME, track_type)
                 for track_type in AVAILABLE_TYPES
                 if track_type.has_binaries(BIN)])

DEFAULT_QUALITY = dict([(track_type.NAME,
                         config.get_default("Quality",
                                            track_type.NAME,
                                            track_type.DEFAULT_COMPRESSION))
                        for track_type in AVAILABLE_TYPES
                        if (len(track_type.COMPRESSION_MODES) > 1)])

if (DEFAULT_TYPE not in TYPE_MAP.keys()):
    DEFAULT_TYPE = "wav"
