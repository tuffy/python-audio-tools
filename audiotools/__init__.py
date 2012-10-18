#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2012  Brian Langenberger

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

"""the core Python Audio Tools module"""

import sys

if (sys.version_info < (2, 6, 0, 'final', 0)):
    print >> sys.stderr, "*** Python 2.6.0 or better required"
    sys.exit(1)


from . import pcm as pcm
import re
import os
import os.path
import ConfigParser
import optparse


class RawConfigParser(ConfigParser.RawConfigParser):
    """extends RawConfigParser to provide additional methods"""

    def get_default(self, section, option, default):
        """returns a default if option is not found in section"""

        try:
            return self.get(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

    def getboolean_default(self, section, option, default):
        """returns a default if option is not found in section"""

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
        """returns a default int if option is not found in section"""

        try:
            return self.getint(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

    def getboolean_default(self, section, option, default):
        """returns a default boolean if option is not found in section"""

        try:
            return self.getboolean(section, option)
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default


config = RawConfigParser()
config.read([os.path.join("/etc", "audiotools.cfg"),
             os.path.join(sys.prefix, "etc", "audiotools.cfg"),
             os.path.expanduser('~/.audiotools.cfg')])

BUFFER_SIZE = 0x100000
FRAMELIST_SIZE = 0x100000 / 4

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

FREEDB_SERVICE = config.getboolean_default("FreeDB", "service", True)
FREEDB_SERVER = config.get_default("FreeDB", "server", "us.freedb.org")
FREEDB_PORT = config.getint_default("FreeDB", "port", 80)

MUSICBRAINZ_SERVICE = config.getboolean_default("MusicBrainz", "service", True)
MUSICBRAINZ_SERVER = config.get_default("MusicBrainz", "server",
                                        "musicbrainz.org")
MUSICBRAINZ_PORT = config.getint_default("MusicBrainz", "port", 80)

ADD_REPLAYGAIN = config.getboolean_default("ReplayGain", "add_by_default",
                                           True)

VERSION = "2.19alpha3"

DEFAULT_FILENAME_FORMAT = '%(track_number)2.2d - %(track_name)s.%(suffix)s'
FILENAME_FORMAT = config.get_default("Filenames", "format",
                                     DEFAULT_FILENAME_FORMAT)

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

#field name -> (field string, text description) mapping
def __format_fields__():
    from .text import (METADATA_TRACK_NAME,
                       METADATA_TRACK_NUMBER,
                       METADATA_TRACK_TOTAL,
                       METADATA_ALBUM_NAME,
                       METADATA_ARTIST_NAME,
                       METADATA_PERFORMER_NAME,
                       METADATA_COMPOSER_NAME,
                       METADATA_CONDUCTOR_NAME,
                       METADATA_MEDIA,
                       METADATA_ISRC,
                       METADATA_CATALOG,
                       METADATA_COPYRIGHT,
                       METADATA_PUBLISHER,
                       METADATA_YEAR,
                       METADATA_DATE,
                       METADATA_ALBUM_NUMBER,
                       METADATA_ALBUM_TOTAL,
                       METADATA_COMMENT,
                       METADATA_SUFFIX,
                       METADATA_ALBUM_TRACK_NUMBER,
                       METADATA_BASENAME)
    return {u"track_name":(u"%(track_name)s",
                           METADATA_TRACK_NAME),
            u"track_number":(u"%(track_number)2.2d",
                             METADATA_TRACK_NUMBER),
            u"track_total":(u"%(track_total)d",
                            METADATA_TRACK_TOTAL),
            u"album_name":(u"%(album_name)s",
                           METADATA_ALBUM_NAME),
            u"artist_name":(u"%(artist_name)s",
                            METADATA_ARTIST_NAME),
            u"performer_name":(u"%(performer_name)s",
                               METADATA_PERFORMER_NAME),
            u"composer_name":(u"%(composer_name)s",
                              METADATA_COMPOSER_NAME),
            u"conductor_name":(u"%(conductor_name)s",
                               METADATA_CONDUCTOR_NAME),
            u"media":(u"%(media)s",
                      METADATA_MEDIA),
            u"ISRC":(u"%(ISRC)s",
                     METADATA_ISRC),
            u"catalog":(u"%(catalog)s",
                        METADATA_CATALOG),
            u"copyright":(u"%(copyright)s",
                          METADATA_COPYRIGHT),
            u"publisher":(u"%(publisher)s",
                          METADATA_PUBLISHER),
            u"year":(u"%(year)s",
                     METADATA_YEAR),
            u"date":(u"%(date)s",
                     METADATA_DATE),
            u"album_number":(u"%(album_number)d",
                             METADATA_ALBUM_NUMBER),
            u"album_total":(u"%(album_total)d",
                            METADATA_ALBUM_TOTAL),
            u"comment":(u"%(comment)s",
                        METADATA_COMMENT),
            u"suffix":(u"%(suffix)s",
                       METADATA_SUFFIX),
            u"album_track_number":(u"%(album_track_number)s",
                                   METADATA_ALBUM_TRACK_NUMBER),
            u"basename":(u"%(basename)s",
                         METADATA_BASENAME)}

FORMAT_FIELDS = __format_fields__()
FORMAT_FIELD_ORDER = (u"track_name",
                      u"artist_name",
                      u"album_name",
                      u"track_number",
                      u"track_total",
                      u"album_number",
                      u"album_total",
                      u"performer_name",
                      u"composer_name",
                      u"conductor_name",
                      u"catalog",
                      U"ISRC",
                      u"publisher",
                      u"media",
                      u"year",
                      u"date",
                      u"copyright",
                      u"comment",
                      u"suffix",
                      u"album_track_number",
                      u"basename")

def __default_quality__(audio_type):
    quality = DEFAULT_QUALITY.get(audio_type, "")
    try:
        if (quality not in TYPE_MAP[audio_type].COMPRESSION_MODES):
            return TYPE_MAP[audio_type].DEFAULT_COMPRESSION
        else:
            return quality
    except KeyError:
        return ""


if (config.has_option("System", "maximum_jobs")):
    MAX_JOBS = config.getint_default("System", "maximum_jobs", 1)
else:
    try:
        import multiprocessing
        MAX_JOBS = multiprocessing.cpucount()
    except (ImportError,AttributeError):
        MAX_JOBS = 1


def get_umask():
    """returns the current file creation umask as an integer

    this is XORed with creation bits integers when used with
    os.open to create new files.  For example:

    >>> fd = os.open(filename, os.WRONLY | os.O_CREAT, 0666 ^ get_umask())
    """

    mask = os.umask(0)
    os.umask(mask)
    return mask


#######################
#Output Messaging
#######################


class OptionParser(optparse.OptionParser):
    """extends OptionParser to use IO_ENCODING as text encoding

    this ensures the encoding remains consistent if --help
    output is piped to a pager vs. sent to a tty
    """

    def _get_encoding(self, file):
        return IO_ENCODING

OptionGroup = optparse.OptionGroup


def Messenger(executable, options):
    """returns a Messenger object based on set verbosity level in options"""

    if (not hasattr(options, "verbosity")):
        return VerboseMessenger(executable)
    elif ((options.verbosity == 'normal') or
          (options.verbosity == 'debug')):
        return VerboseMessenger(executable)
    else:
        return SilentMessenger(executable)

__ANSI_SEQUENCE__ = re.compile(u"\u001B\[[0-9;]+.")
__CHAR_WIDTHS__ = {"Na": 1,
                   "A": 1,
                   "W": 2,
                   "F": 2,
                   "N": 1,
                   "H": 1}


def khz(hz):
    """given an integer sample rate value in Hz,
    returns a unicode kHz value with suffix

    the string is typically 7-8 characters wide"""

    num = hz / 1000
    den = (hz % 1000) / 100
    if (den == 0):
        return u"%dkHz" % (num)
    else:
        return u"%d.%dkHz" % (num, den)


def str_width(s):
    """returns the width of unicode string s, in characters

    this accounts for multi-code Unicode characters
    as well as embedded ANSI sequences
    """

    import unicodedata

    return sum(
        [__CHAR_WIDTHS__.get(unicodedata.east_asian_width(char), 1) for char in
         unicodedata.normalize('NFC', __ANSI_SEQUENCE__.sub(u"", s))])


class display_unicode:
    """a class for abstracting unicode string truncation

    this is necessary because not all Unicode characters are
    the same length when displayed onscreen
    """

    def __init__(self, unicode_string):
        import unicodedata

        self.__string__ = unicodedata.normalize(
            'NFC',
            __ANSI_SEQUENCE__.sub(u"", unicode(unicode_string)))
        self.__char_widths__ = tuple(
            [__CHAR_WIDTHS__.get(unicodedata.east_asian_width(char), 1)
             for char in self.__string__])

    def __unicode__(self):
        return self.__string__

    def __len__(self):
        return sum(self.__char_widths__)

    def __repr__(self):
        return "display_unicode(%s)" % (repr(self.__string__))

    def __add__(self, unicode_string):
        return display_unicode(self.__string__ + unicode(unicode_string))

    def head(self, display_characters):
        """returns a display_unicode object truncated to the given length

        characters at the end of the string are removed as needed"""

        output_chars = []
        for (char, width) in zip(self.__string__, self.__char_widths__):
            if (width <= display_characters):
                output_chars.append(char)
                display_characters -= width
            else:
                break
        return display_unicode(u"".join(output_chars))

    def tail(self, display_characters):
        """returns a display_unicode object truncated to the given length

        characters at the beginning of the string are removed as needed"""

        output_chars = []
        for (char, width) in zip(reversed(self.__string__),
                                 reversed(self.__char_widths__)):
            if (width <= display_characters):
                output_chars.append(char)
                display_characters -= width
            else:
                break

        output_chars.reverse()
        return display_unicode(u"".join(output_chars))

    def split(self, display_characters):
        """returns a tuple of display_unicode objects

        the first is up to 'display_characters' in length
        the second contains the remainder of the string
        """

        head_chars = []
        tail_chars = []
        for (char, width) in zip(self.__string__, self.__char_widths__):
            if (width <= display_characters):
                head_chars.append(char)
                display_characters -= width
            else:
                tail_chars.append(char)
                display_characters = -1

        return (display_unicode(u"".join(head_chars)),
                display_unicode(u"".join(tail_chars)))


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
    """this class is for displaying formatted output in a consistent way

    it performs proper unicode string encoding based on IO_ENCODING,
    but can also display tabular data and ANSI-escaped data
    with less effort
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
        """executable is a plain string of what script is being run

        this is typically for use by the usage() method"""

        self.executable = executable
        self.output_msg_rows = []  # a list of __MessengerRow__ objects

    def output(self, s):
        """displays an output message unicode string to stdout

        this appends a newline to that message"""

        sys.stdout.write(s.encode(IO_ENCODING, 'replace'))
        sys.stdout.write(os.linesep)

    def partial_output(self, s):
        """displays a partial output message unicode string to stdout

        this flushes output so that message is displayed"""

        sys.stdout.write(s.encode(IO_ENCODING, 'replace'))
        sys.stdout.flush()

    def new_row(self):
        """sets up a new tabbed row for outputting aligned text

        this must be called prior to calling output_column()"""

        self.output_msg_rows.append(__MessengerRow__())

    def blank_row(self):
        """generates a completely blank row of aligned text

        this cannot be the first row of aligned text"""

        if (len(self.output_msg_rows) == 0):
            raise ValueError("first output row cannot be blank")
        else:
            self.new_row()
            for i in xrange(len(self.output_msg_rows[0].lengths())):
                self.output_column(u"")

    def divider_row(self, dividers):
        """adds a row of unicode divider characters

        there should be one character in dividers per output column
        for example:
        >>> m = VerboseMessenger("audiotools")
        >>> m.new_row()
        >>> m.output_column(u'Foo')
        >>> m.output_column(u' ')
        >>> m.output_column(u'Bar')
        >>> m.divider_row([u'-',u' ',u'-'])
        >>> m.output_rows()
        foo Bar
        --- ---

        """

        self.output_msg_rows.append(__DividerRow__(dividers))

    def output_column(self, string, right_aligned=False):
        """adds a column of aligned unicode data"""

        if (len(self.output_msg_rows) > 0):
            self.output_msg_rows[-1].add_string(string, right_aligned)
        else:
            raise ValueError(
                "you must perform \"new_row\" before adding columns")

    def output_rows(self):
        """outputs all of our accumulated output rows as aligned output

        this operates by calling our output() method
        therefore, subclasses that have overridden output() to noops
        (silent messengers) will also have silent output_rows() methods
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
        """displays an informative message unicode string to stderr

        this appends a newline to that message"""

        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def info_rows(self):
        """outputs all of our accumulated output rows as aligned info

        this operates by calling our info() method
        therefore, subclasses that have overridden info() to noops
        (silent messengers) will also have silent info_rows() methods
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
        """displays a partial informative message unicode string to stdout

        this flushes output so that message is displayed"""

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
        """displays an error message unicode string to stderr

        this appends a newline to that message"""

        sys.stderr.write("*** Error: ")
        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def os_error(self, oserror):
        """displays an properly formatted OSError exception to stderr

        this appends a newline to that message"""

        self.error(u"[Errno %d] %s: '%s'" % \
                       (oserror.errno,
                        oserror.strerror.decode('utf-8', 'replace'),
                        Filename(oserror.filename)))

    def warning(self, s):
        """displays a warning message unicode string to stderr

        this appends a newline to that message"""

        sys.stderr.write("*** Warning: ")
        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def usage(self, s):
        """displays the program's usage unicode string to stderr

        this appends a newline to that message"""

        sys.stderr.write("*** Usage: ")
        sys.stderr.write(self.executable.decode('ascii'))
        sys.stderr.write(" ")
        sys.stderr.write(s.encode(IO_ENCODING, 'replace'))
        sys.stderr.write(os.linesep)

    def ansi(self, s, codes):
        """generates an ANSI code as a unicode string

        takes a unicode string to be escaped
        and a list of ANSI SGR codes
        returns an ANSI-escaped unicode terminal string
        with those codes activated followed by the unescaped code
        if the Messenger's stdout is to a tty terminal
        otherwise, the string is returned unmodified

        for example:
        >>> VerboseMessenger("audiotools").ansi(u"foo",
        ...                                     [VerboseMessenger.BOLD])
        u'\\x1b[1mfoo\\x1b[0m'
        """

        if (sys.stdout.isatty()):
            return u"\u001B[%sm%s\u001B[0m" % \
                (";".join(map(unicode, codes)), s)
        else:
            return s

    def ansi_clearline(self):
        """generates a set of clear line ANSI escape codes to stdout

        this works only if stdout is a tty.  Otherwise, it does nothing
        for example:
        >>> msg = VerboseMessenger("audiotools")
        >>> msg.partial_output(u"working")
        >>> time.sleep(1)
        >>> msg.ansi_clearline()
        >>> msg.output(u"done")
        """

        if (sys.stdout.isatty()):
            sys.stdout.write((
                    # move cursor to column 0
                    u"\u001B[0G" +
                    # clear everything after cursor
                    u"\u001B[0K").encode(IO_ENCODING))
            sys.stdout.flush()

    def ansi_uplines(self, lines):
        """moves the cursor up by the given number of lines"""

        if (sys.stdout.isatty()):
            sys.stdout.write(u"\u001B[%dA" % (lines))
            sys.stdout.flush()

    def ansi_cleardown(self):
        """clears the remainder of the screen from the cursor downward"""

        if (sys.stdout.isatty()):
            sys.stdout.write(u"\u001B[0J")
            sys.stdout.flush()

    def ansi_clearscreen(self):
        """clears the entire screen and moves cursor to upper left corner"""

        if (sys.stdout.isatty()):
            sys.stdout.write(u"\u001B[2J")
            sys.stdout.write(u"\u001B[1;1H")
            sys.stdout.flush()

    def ansi_err(self, s, codes):
        """generates an ANSI code as a unicode string

        takes a unicode string to be escaped
        and a list of ANSI SGR codes
        returns an ANSI-escaped unicode terminal string
        with those codes activated followed by the unescaped code
        if the Messenger's stderr is to a tty terminal
        otherwise, the string is returned unmodified"""

        if (sys.stderr.isatty()):
            return u"\u001B[%sm%s\u001B[0m" % \
                (";".join(map(unicode, codes)), s)
        else:
            return s

    def terminal_size(self, fd):
        """returns the current terminal size as (height, width)"""

        import fcntl
        import termios
        import struct

        #this isn't all that portable, but will have to do
        return struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))


class SilentMessenger(VerboseMessenger):
    def output(self, s):
        """performs no output, resulting in silence"""

        pass

    def partial_output(self, s):
        """performs no output, resulting in silence"""

        pass

    def warning(self, s):
        """performs no output, resulting in silence"""

        pass

    def info(self, s):
        """performs no output, resulting in silence"""

        pass

    def partial_info(self, s):
        """performs no output, resulting in silence"""

        pass

    def ansi_clearline(self):
        """performs no output, resulting in silence"""

        pass

    def ansi_uplines(self, lines):
        """performs no output, resulting in silence"""

        pass

    def ansi_cleardown(self):
        """performs no output, resulting in silence"""

        pass


class ProgressDisplay:
    """a class for displaying incremental progress updates to the screen"""

    def __init__(self, messenger):
        """takes a Messenger object for displaying output"""

        self.messenger = messenger
        self.progress_rows = []
        self.previous_output = []

        if (sys.stdout.isatty()):
            self.add_row = self.add_row_tty
            self.delete_row = self.delete_row_tty
            self.update_row = self.update_row_tty
            self.refresh = self.refresh_tty
            self.clear = self.clear_tty
        else:
            self.add_row = self.add_row_nontty
            self.delete_row = self.delete_row_nontty
            self.update_row = self.update_row_nontty
            self.refresh = self.refresh_nontty
            self.clear = self.clear_nontty

    def add_row_tty(self, row_id, output_line):
        """adds a row of output to be displayed with progress indicated

        row_id should be a unique identifier
        output_line should be a unicode string"""

        new_row = ProgressRow(row_id, output_line)
        if (None in self.progress_rows):
            self.progress_rows[self.progress_rows.index(None)] = new_row
        else:
            self.progress_rows.append(new_row)

    def add_row_nontty(self, row_id, output_line):
        """adds a row of output to be displayed with progress indicated

        row_id should be a unique identifier
        output_line should be a unicode string"""

        pass

    def delete_row_tty(self, row_id):
        """removes the row with the given ID"""

        row_index = None
        for (i, row) in enumerate(self.progress_rows):
            if ((row is not None) and (row.id == row_id)):
                row_index = i
                break

        if (row_index is not None):
            self.progress_rows[row_index] = None

    def delete_row_nontty(self, row_id):
        """removes the row with the given ID"""

        pass

    def update_row_tty(self, row_id, current, total):
        """updates the given row with a new current and total status"""

        for row in self.progress_rows:
            if ((row is not None) and (row.id == row_id)):
                row.update(current, total)

    def update_row_nontty(self, row_id, current, total):
        """updates the given row with a new current and total status"""

        pass

    def refresh_tty(self):
        """refreshes the display of all status rows

        this deletes and redraws output as necessary,
        depending on whether output has changed since
        previously displayed"""

        (screen_height,
         screen_width) = self.messenger.terminal_size(sys.stdout)
        new_output = [progress_row.unicode(screen_width)
                      for progress_row in self.progress_rows
                      if progress_row is not None][0:screen_height - 1]
        for output in new_output:
            self.messenger.output(output)
        self.previous_output = new_output

    def refresh_nontty(self):
        """refreshes the display of all status rows

        this deletes and redraws output as necessary,
        depending on whether output has changed since
        previously displayed"""

        pass

    def clear_tty(self):
        """clears all previously displayed output"""

        if (len(self.previous_output) > 0):
            self.messenger.ansi_clearline()
            self.messenger.ansi_uplines(len(self.previous_output))
            self.messenger.ansi_cleardown()
            self.previous_output = []

    def clear_nontty(self):
        """clears all previously displayed output"""

        pass


class SingleProgressDisplay(ProgressDisplay):
    """a specialized ProgressDisplay for handling a single line of output"""

    def __init__(self, messenger, progress_text):
        """takes a Messenger class and unicode string for output"""

        ProgressDisplay.__init__(self, messenger)
        self.add_row(0, progress_text)

        from time import time

        self.time = time
        self.last_updated = 0

    def update(self, current, total):
        """updates the output line with new current and total values"""

        now = self.time()
        if ((now - self.last_updated) > 0.25):
            self.clear()
            self.update_row(0, current, total)
            self.refresh()
            self.last_updated = now

class ReplayGainProgressDisplay(ProgressDisplay):
    """a specialized ProgressDisplay for handling ReplayGain application"""

    def __init__(self, messenger, lossless_replay_gain):
        """takes a Messenger and whether ReplayGain is lossless or not"""

        ProgressDisplay.__init__(self, messenger)

        from time import time
        from .text import (RG_ADDING_REPLAYGAIN,
                           RG_APPLYING_REPLAYGAIN)

        self.time = time
        self.last_updated = 0

        self.lossless_replay_gain = lossless_replay_gain
        if (lossless_replay_gain):
            self.add_row(0, RG_ADDING_REPLAYGAIN)
        else:
            self.add_row(0, RG_APPLYING_REPLAYGAIN)

        if (sys.stdout.isatty()):
            self.initial_message = self.initial_message_tty
            self.update = self.update_tty
            self.final_message = self.final_message_tty
            self.replaygain_row = self.progress_rows[0]
        else:
            self.initial_message = self.initial_message_nontty
            self.update = self.update_nontty
            self.final_message = self.final_message_nontty

    def initial_message_tty(self):
        """displays a message that ReplayGain application has started"""

        pass

    def initial_message_nontty(self):
        """displays a message that ReplayGain application has started"""

        from .text import (RG_ADDING_REPLAYGAIN_WAIT,
                           RG_APPLYING_REPLAYGAIN_WAIT)

        if (self.lossless_replay_gain):
            self.messenger.info(RG_ADDING_REPLAYGAIN_WAIT)
        else:
            self.messenger.info(RG_APPLYING_REPLAYGAIN_WAIT)

    def update_tty(self, current, total):
        """updates the current status of ReplayGain application"""

        now = self.time()
        if ((now - self.last_updated) > 0.25):
            self.clear()
            self.replaygain_row.update(current, total)
            self.refresh()
            self.last_updated = now

    def update_nontty(self, current, total):
        """updates the current status of ReplayGain application"""

        pass

    def final_message_tty(self):
        """displays a message that ReplayGain application is complete"""

        from .text import (RG_REPLAYGAIN_ADDED,
                           RG_REPLAYGAIN_APPLIED)

        self.clear()
        if (self.lossless_replay_gain):
            self.messenger.info(RG_REPLAYGAIN_ADDED)
        else:
            self.messenger.info(RG_REPLAYGAIN_APPLIED)

    def final_message_nontty(self):
        """displays a message that ReplayGain application is complete"""

        pass


class ProgressRow:
    """a class for displaying a single row of progress output"""

    def __init__(self, row_id, output_line):
        """row_id is a unique identifier.  output_line is a unicode string"""

        from time import time

        self.id = row_id
        self.output_line = display_unicode(output_line)
        self.current = 0
        self.total = 0
        self.start_time = time()

        self.ansi = VerboseMessenger("").ansi

    def update(self, current, total):
        """updates our row with the current progress values"""

        self.current = current
        self.total = total

    def unicode(self, width):
        """returns a unicode string formatted to the given width"""

        from time import time

        try:
            time_spent = time() - self.start_time

            split_point = (width * self.current) / self.total
            estimated_total_time = (time_spent * self.total) / self.current
            estimated_time_remaining = int(round(estimated_total_time -
                                                 time_spent))
            time_remaining = u" %2.1d:%2.2d" % (estimated_time_remaining / 60,
                                                estimated_time_remaining % 60)
        except ZeroDivisionError:
            split_point = 0
            time_remaining = u" --:--"

        output_line_width = width - len(time_remaining)

        if (len(self.output_line) < output_line_width):
            output_line = self.output_line
        else:
            output_line = self.output_line.tail(output_line_width)

        output_line += (u" " * (output_line_width - len(output_line)) +
                        time_remaining)

        (head, tail) = output_line.split(split_point)
        output_line = (self.ansi(unicode(head),
                                 [VerboseMessenger.FG_WHITE,
                                  VerboseMessenger.BG_BLUE]) +
                       unicode(tail))

        return output_line


class UnsupportedFile(Exception):
    """raised by open() if the file can be opened but not identified"""

    pass


class InvalidFile(Exception):
    """raised during initialization if the file is invalid in some way"""

    pass


class InvalidFormat(Exception):
    """raised if an audio file cannot be created correctly from from_pcm()
    due to having a PCM format unsupported by the output format"""

    pass


class EncodingError(IOError):
    """raised if an audio file cannot be created correctly from from_pcm()
    due to an error by the encoder"""

    def __init__(self, error_message):
        IOError.__init__(self)
        self.error_message = error_message

    def __reduce__(self):
        return (EncodingError, (self.error_message, ))

    def __str__(self):
        if (isinstance(self.error_message, unicode)):
            return self.error_message.encode('ascii', 'replace')
        else:
            return str(self.error_message)

    def __unicode__(self):
        return unicode(self.error_message)


class UnsupportedChannelMask(EncodingError):
    """raised if the encoder does not support the file's channel mask"""

    def __init__(self, filename, mask):
        from .text import ERR_UNSUPPORTED_CHANNEL_MASK

        EncodingError.__init__(
            self,
            ERR_UNSUPPORTED_CHANNEL_MASK %
            {"target_filename": Filename(filename),
             "assignment": ChannelMask(mask)})


class UnsupportedChannelCount(EncodingError):
    """raised if the encoder does not support the file's channel count"""

    def __init__(self, filename, count):
        from .text import ERR_UNSUPPORTED_CHANNEL_COUNT

        EncodingError.__init__(
            self,
            ERR_UNSUPPORTED_CHANNEL_COUNT %
            {"target_filename": Filename(filename),
             "channels": count})


class UnsupportedBitsPerSample(EncodingError):
    """raised if the encoder does not support the file's bits-per-sample"""

    def __init__(self, filename, bits_per_sample):
        from .text import ERR_UNSUPPORTED_BITS_PER_SAMPLE

        EncodingError.__init__(
            self,
            ERR_UNSUPPORTED_BITS_PER_SAMPLE %
            {"target_filename": Filename(filename),
             "bps": bits_per_sample})


class DecodingError(IOError):
    """raised if the decoder exits with an error

    typically, a from_pcm() method will catch this error
    and raise EncodingError"""

    def __init__(self, error_message):
        IOError.__init__(self)
        self.error_message = error_message


def file_type(file):
    """given a seekable file stream rewound to the file's start
    returns an AudioFile-compatible class that stream is a type of
    or None of the stream's type is unknown

    the AudioFile class is not guaranteed to be available"""

    header = file.read(37)
    if ((header[4:8] == "ftyp") and
        (header[8:12] in ('mp41', 'mp42', 'M4A ', 'M4B '))):
        #possibly ALAC or M4A

        from .bitstream import BitstreamReader
        from .m4a import get_m4a_atom

        file.seek(0, 0)
        reader = BitstreamReader(file, 0)

        #so get contents of moov->trak->mdia->minf->stbl->stsd atom
        try:
            stsd = get_m4a_atom(reader,
                                "moov", "trak", "mdia",
                                "minf", "stbl", "stsd")[1]
            (stsd_version, descriptions,
             atom_size, atom_type) = stsd.parse("8u 24p 32u 32u 4b")

            if (atom_type == "alac"):
                #if first description is "alac" atom, it's an ALAC
                return ALACAudio
            elif (atom_type == "mp4a"):
                #if first description is "mp4a" atom, it's M4A
                return M4AAudio
            else:
                #otherwise, it's unknown
                return None
        except KeyError:
            #no stsd atom, so unknown
            return None
        except IOError:
            #error reading atom, so unknown
            return None
    elif ((header[0:4] == "FORM") and (header[8:12] == "AIFF")):
        return AiffAudio
    elif (header[0:4] == ".snd"):
        return AuAudio
    elif (header[0:4] == "fLaC"):
        return FlacAudio
    elif ((len(header) >= 4) and (header[0] == "\xFF")):
        #possibly MP3 or MP2

        from .bitstream import BitstreamReader
        from cStringIO import StringIO

        #header is at least 32 bits, so no IOError is possible
        (frame_sync,
         mpeg_id,
         layer_description,
         protection,
         bitrate,
         sample_rate,
         pad,
         private,
         channels,
         mode_extension,
         copy,
         original,
         emphasis) = BitstreamReader(StringIO(header), 0).parse(
            "11u 2u 2u 1u 4u 2u 1u 1u 2u 2u 1u 1u 2u")
        if ((frame_sync == 0x7FF) and
            (mpeg_id == 3) and
            (layer_description == 1) and
            (bitrate != 0xF) and
            (sample_rate != 3) and
            (emphasis != 2)):
            #MP3s are MPEG-1, Layer-III
            return MP3Audio
        elif ((frame_sync == 0x7FF) and
              (mpeg_id == 3) and
              (layer_description == 2) and
              (bitrate != 0xF) and
              (sample_rate != 3) and
              (emphasis != 2)):
            #MP2s are MPEG-1, Layer-II
            return MP2Audio
        else:
            #nothing else starts with an initial byte of 0xFF
            #so the file is unknown
            return None
    elif (header[0:4] == "OggS"):
        #possibly Ogg FLAC, Ogg Vorbis or Ogg Opus
         if (header[0x1C:0x21] == "\x7FFLAC"):
             return OggFlacAudio
         elif (header[0x1C:0x23] == "\x01vorbis"):
             return VorbisAudio
         elif (header[0x1C:0x26] == "OpusHead\x01"):
             return OpusAudio
         else:
             return None
    elif (header[0:5] == "ajkg\x02"):
        return ShortenAudio
    elif (header[0:4] == "wvpk"):
        return WavPackAudio
    elif ((header[0:4] == "RIFF") and (header[8:12] == "WAVE")):
        return WaveAudio
    elif ((len(header) >= 10) and
          (header[0:3] == "ID3") and
          (ord(header[3]) in (2, 3, 4))):
        #file contains ID3v2 tag
        #so it may be MP3, MP2 or FLAC

        #determine sync-safe tag size and skip entire tag
        tag_size = 0
        for b in header[6:10]:
            tag_size = (tag_size << 7) | (ord(b) % 0x7F)
        file.seek(10 + tag_size, 0)
        b = file.read(1)
        while (b == "\x00"):
            #skip NULL bytes after ID3v2 tag
            b = file.read(1)

        if (b == ""):
            #no data after tag, so file is unknown
            return None
        elif (b == "\xFF"):
            #possibly MP3 or MP2 file

            from .bitstream import BitstreamReader

            try:
                (frame_sync,
                 mpeg_id,
                 layer_description,
                 protection,
                 bitrate,
                 sample_rate,
                 pad,
                 private,
                 channels,
                 mode_extension,
                 copy,
                 original,
                 emphasis) = BitstreamReader(file, 0).parse(
                    "3u 2u 2u 1u 4u 2u 1u 1u 2u 2u 1u 1u 2u")
                if ((frame_sync == 0x7) and
                    (mpeg_id == 3) and
                    (layer_description == 1) and
                    (bitrate != 0xF) and
                    (sample_rate != 3) and
                    (emphasis != 2)):
                    #MP3s are MPEG-1, Layer-III
                    return MP3Audio
                elif ((frame_sync == 0x7) and
                      (mpeg_id == 3) and
                      (layer_description == 2) and
                      (bitrate != 0xF) and
                      (sample_rate != 3) and
                      (emphasis != 2)):
                    #MP2s are MPEG-1, Layer-II
                    return MP2Audio
                else:
                    #nothing else starts with an initial byte of 0xFF
                    #so the file is unknown
                    return None
            except IOError:
                return None
        elif (b == "f"):
            #possibly FLAC file
            if (file.read(3) == "LaC"):
                return FlacAudio
            else:
                return None
        else:
            #unknown file after ID3 tag
            return None
    else:
        return None


def open(filename):
    """returns an AudioFile located at the given filename path

    this works solely by examining the file's contents
    after opening it
    raises UnsupportedFile if it's not a file we support based on its headers
    raises InvalidFile if the file appears to be something we support,
    but has errors of some sort
    raises IOError if some problem occurs attempting to open the file
    """

    f = file(filename, "rb")
    try:
        audio_class = file_type(f)
        if ((audio_class is not None) and
            (audio_class.has_binaries(BIN))):
            return audio_class(filename)
        else:
            raise UnsupportedFile(filename)
    finally:
        f.close()


class DuplicateFile(Exception):
    """raised if the same file is included more than once"""

    def __init__(self, filename):
        """filename is a Filename object"""

        self.filename = filename

    def __unicode__(self):
        from .text import ERR_DUPLICATE_FILE

        return ERR_DUPLICATE_FILE % (self.filename,)


class DuplicateOutputFile(Exception):
    """raised if the same output file is generated more than once"""

    def __init__(self, filename):
        """filename is a Filename object"""

        self.filename = filename

    def __unicode__(self):
        from .text import ERR_DUPLICATE_OUTPUT_FILE

        return ERR_DUPLICATE_OUTPUT_FILE % (self.filename,)


class OutputFileIsInput(Exception):
    """raised if an output file is the same as an input file"""

    def __init__(self, filename):
        """filename is a Filename object"""

        self.filename = filename

    def __unicode__(self):
        from .text import ERR_OUTPUT_IS_INPUT

        return ERR_OUTPUT_IS_INPUT % (self.filename,)


class Filename(tuple):
    def __new__(cls, filename):
        """filename is a string of the file on disk"""

        filename = str(filename)
        try:
            stat = os.stat(filename)
            return tuple.__new__(cls, [os.path.normpath(filename),
                                       stat.st_dev,
                                       stat.st_ino])
        except OSError:
            return tuple.__new__(cls, [os.path.normpath(filename),
                                       None,
                                       None])

    def disk_file(self):
        """returns True if the file exists on disk"""

        return (self[1] is not None) and (self[2] is not None)

    def basename(self):
        """returns the basename (no directory) of this file"""

        return Filename(os.path.basename(self[0]))

    def expanduser(self):
        """returns a Filename object with user directory expanded"""

        return Filename(os.path.expanduser(self[0]))

    def __repr__(self):
        return "Filename(%s, %s, %s)" % \
            (repr(self[0]), repr(self[1]), repr(self[2]))

    def __eq__(self, filename):
        if (isinstance(filename, Filename)):
            if (self.disk_file() and filename.disk_file()):
                #both exist on disk,
                #so they compare equally if st_dev and st_ino match
                return (self[1] == filename[1]) and (self[2] == filename[2])
            elif ((not self.disk_file()) and (not filename.disk_file())):
                #neither exist on disk,
                #so they compare equally if their paths match
                return self[0] == filename[0]
            else:
                #one or the other exists on disk
                #but not both, so they never match
                return False
        else:
            return False

    def __ne__(self, filename):
        return not self == filename

    def __hash__(self):
        if (self.disk_file()):
            return hash((None, self[1], self[2]))
        else:
            return hash((self[0], self[1], self[2]))

    def __str__(self):
        return self[0]

    def __unicode__(self):
        return self[0].decode(FS_ENCODING, "replace")


#takes a list of filenames
#returns a list of AudioFile objects, sorted by track_number()
#any unsupported files are filtered out
def open_files(filename_list, sorted=True, messenger=None,
               no_duplicates=False, warn_duplicates=False,
               opened_files=None):
    """returns a list of AudioFile objects
    from a list of filename strings or Filename objects

    if "sorted" is True, files are sorted by album number then track number

    if "messenger" is given, warnings and errors when opening files
    are sent to the given Messenger-compatible object

    if "no_duplicates" is True, including the same file twice
    raises a DuplicateFile whose filename value
    is the first duplicate filename as a Filename object

    if "warn_duplicates" is True, including the same file twice
    results in a warning message to the messenger object, if given

    "opened_files" is a set object containing previously opened
    Filename objects and which newly opened Filename objects are added to
    """

    from .text import (ERR_DUPLICATE_FILE,
                       ERR_OPEN_IOERROR)

    if (opened_files is None):
        opened_files = set([])

    toreturn = []

    for filename in map(Filename, filename_list):
        try:
            if (filename in opened_files):
                if (no_duplicates):
                    raise DuplicateFile(filename)
                elif (warn_duplicates and (messenger is not None)):
                    messenger.warning(ERR_DUPLICATE_FILE % (filename,))
            else:
                opened_files.add(filename)

            toreturn.append(open(str(filename)))
        except UnsupportedFile:
            pass
        except IOError, err:
            if (messenger is not None):
                messenger.warning(ERR_OPEN_IOERROR % (filename,))
        except InvalidFile, err:
            if (messenger is not None):
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
    """yields an AudioFile via a recursive search of directory

    files are sorted by album number/track number by default,
    on a per-directory basis
    any unsupported files are filtered out
    error messages are sent to messenger, if given
    """

    for (basedir, subdirs, filenames) in os.walk(directory):
        if (sorted):
            subdirs.sort()
        for audiofile in open_files([os.path.join(basedir, filename)
                                     for filename in filenames],
                                    sorted=sorted,
                                    messenger=messenger):
            yield audiofile


def group_tracks(tracks):
    """takes an iterable collection of tracks

    yields list of tracks grouped by album
    where their album_name and album_number match, if possible"""

    collection = {}
    for track in tracks:
        metadata = track.get_metadata()
        collection.setdefault(
            (track.album_number(),
             metadata.album_name
             if metadata is not None else None), []).append(track)

    for key in sorted(collection.keys()):
        yield collection[key]


class UnknownAudioType(Exception):
    """raised if filename_to_type finds no possibilities"""

    def __init__(self, suffix):
        self.suffix = suffix

    def error_msg(self, messenger):
        from .text import ERR_UNSUPPORTED_AUDIO_TYPE

        messenger.error(ERR_UNSUPPORTED_AUDIO_TYPE % (self.suffix,))


class AmbiguousAudioType(UnknownAudioType):
    """raised if filename_to_type finds more than one possibility"""

    def __init__(self, suffix, type_list):
        self.suffix = suffix
        self.type_list = type_list

    def error_msg(self, messenger):
        from .text import (ERR_AMBIGUOUS_AUDIO_TYPE,
                           LAB_USE_T_OPTION)

        messenger.error(ERR_AMBIGUOUS_AUDIO_TYPE % (self.suffix,))
        messenger.info(LAB_USE_T_OPTION %
                       (u" or ".join([u"\"%s\"" % (t.NAME.decode('ascii'))
                                      for t in self.type_list])))


def filename_to_type(path):
    """given a path to a file, return its audio type based on suffix

    for example:
    >>> filename_to_type("/foo/file.flac")
    <class audiotools.__flac__.FlacAudio at 0x7fc8456d55f0>

    raises an UnknownAudioType exception if the type is unknown
    raise AmbiguousAudioType exception if the type is ambiguous
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
    """an integer-like class that abstracts a PCMReader's channel assignments

    all channels in a FrameList will be in RIFF WAVE order
    as a sensible convention
    but which channel corresponds to which speaker is decided by this mask
    for example, a 4 channel PCMReader with the channel mask 0x33
    corresponds to the bits 00110011
    reading those bits from right to left (least significant first)
    the "front_left", "front_right", "back_left", "back_right"
    speakers are set

    therefore, the PCMReader's 4 channel FrameLists are laid out as follows:

    channel 0 -> front_left
    channel 1 -> front_right
    channel 2 -> back_left
    channel 3 -> back_right

    since the "front_center" and "low_frequency" bits are not set,
    those channels are skipped in the returned FrameLists

    many formats store their channels internally in a different order
    their PCMReaders will be expected to reorder channels
    and set a ChannelMask matching this convention
    and, their from_pcm() functions will be expected to reverse the process

    a ChannelMask of 0 is "undefined",
    which means that channels aren't assigned to *any* speaker
    this is an ugly last resort for handling formats
    where multi-channel assignments aren't properly defined
    in this case, a from_pcm() method is free to assign the undefined channels
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

    from .text import (MASK_FRONT_LEFT,
                       MASK_FRONT_RIGHT,
                       MASK_FRONT_CENTER,
                       MASK_LFE,
                       MASK_BACK_LEFT,
                       MASK_BACK_RIGHT,
                       MASK_FRONT_RIGHT_OF_CENTER,
                       MASK_FRONT_LEFT_OF_CENTER,
                       MASK_BACK_CENTER,
                       MASK_SIDE_LEFT,
                       MASK_SIDE_RIGHT,
                       MASK_TOP_CENTER,
                       MASK_TOP_FRONT_LEFT,
                       MASK_TOP_FRONT_CENTER,
                       MASK_TOP_FRONT_RIGHT,
                       MASK_TOP_BACK_LEFT,
                       MASK_TOP_BACK_CENTER,
                       MASK_TOP_BACK_RIGHT)

    MASK_TO_NAME = {0x1: MASK_FRONT_LEFT,
                    0x2: MASK_FRONT_RIGHT,
                    0x4: MASK_FRONT_CENTER,
                    0x8: MASK_LFE,
                    0x10: MASK_BACK_LEFT,
                    0x20: MASK_BACK_RIGHT,
                    0x40: MASK_FRONT_RIGHT_OF_CENTER,
                    0x80: MASK_FRONT_LEFT_OF_CENTER,
                    0x100: MASK_BACK_CENTER,
                    0x200: MASK_SIDE_LEFT,
                    0x400: MASK_SIDE_RIGHT,
                    0x800: MASK_TOP_CENTER,
                    0x1000: MASK_TOP_FRONT_LEFT,
                    0x2000: MASK_TOP_FRONT_CENTER,
                    0x4000: MASK_TOP_FRONT_RIGHT,
                    0x8000: MASK_TOP_BACK_LEFT,
                    0x10000: MASK_TOP_BACK_CENTER,
                    0x20000: MASK_TOP_BACK_RIGHT}

    def __init__(self, mask):
        """mask should be an integer channel mask value"""

        mask = int(mask)

        for (speaker, speaker_mask) in self.SPEAKER_TO_MASK.items():
            setattr(self, speaker, (mask & speaker_mask) != 0)

    def __unicode__(self):
        return u", ".join([self.MASK_TO_NAME[key] for key in
                          sorted(self.MASK_TO_SPEAKER.keys())
                          if getattr(self, self.MASK_TO_SPEAKER[key])])

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
        """returns True if this ChannelMask is defined"""

        return int(self) != 0

    def undefined(self):
        """returns True if this ChannelMask is undefined"""

        return int(self) == 0

    def channels(self):
        """returns a list of speaker strings this mask contains

        returned in the order in which they should appear
        in the PCM stream
        """

        c = []
        for (mask, speaker) in sorted(self.MASK_TO_SPEAKER.items(),
                                      lambda x, y: cmp(x[0], y[0])):
            if (getattr(self, speaker)):
                c.append(speaker)

        return c

    def index(self, channel_name):
        """returns the index of the given channel name within this mask

        for example, given the mask 0xB (fL, fR, LFE, but no fC)
        index("low_frequency") will return 2
        if the channel is not in this mask, raises ValueError"""

        return self.channels().index(channel_name)

    @classmethod
    def from_fields(cls, **fields):
        """given a set of channel arguments, returns a new ChannelMask

        for example:
        >>> ChannelMask.from_fields(front_left=True,front_right=True)
        channelMask(front_right=True,front_left=True)
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
        """given a channel count, returns a new ChannelMask

        this is only valid for channel counts 1 and 2
        all other values trigger a ValueError"""

        if (channel_count == 2):
            return cls(0x3)
        elif (channel_count == 1):
            return cls(0x4)
        else:
            raise ValueError("ambiguous channel assignment")


class PCMReader:
    """a class that wraps around a file object and generates pcm.FrameLists"""

    def __init__(self, file,
                 sample_rate, channels, channel_mask, bits_per_sample,
                 process=None, signed=True, big_endian=False):
        """fields are as follows:

        file            - a file-like object with read() and close() methods
        sample_rate     - an integer number of Hz
        channels        - an integer number of channels
        channel_mask    - an integer channel mask value
        bits_per_sample - an integer number of bits per sample
        process         - an optional subprocess object
        signed          - True if the file's samples are signed integers
        big_endian      - True if the file's samples are stored big-endian

        the process, signed and big_endian arguments are optional
        pCMReader-compatible objects need only expose the
        sample_rate, channels, channel_mask and bits_per_sample fields
        along with the read() and close() methods
        """

        self.file = file
        self.sample_rate = sample_rate
        self.channels = channels
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample
        self.process = process
        self.signed = signed
        self.big_endian = big_endian

    def read(self, pcm_frames):
        """try to read the given number of PCM frames from the stream

        this is *not* guaranteed to read exactly that number of frames
        it may return less (at the end of the stream, especially)
        it may return more
        however, it must always return a non-empty FrameList until the
        end of the PCM stream is reached

        may raise IOError if unable to read the input file,
        or ValueError if the input file has some sort of error
        """

        return pcm.FrameList(
            self.file.read(max(pcm_frames, 1) *
                           self.channels * (self.bits_per_sample / 8)),
            self.channels,
            self.bits_per_sample,
            self.big_endian,
            self.signed)

    def close(self):
        """closes the stream for reading

        any subprocess is waited for also so for proper cleanup
        may return DecodingError if a helper subprocess exits
        with an error status"""

        self.file.close()

        if (self.process is not None):
            if (self.process.wait() != 0):
                raise DecodingError(u"subprocess exited with error")


class PCMReaderError(PCMReader):
    """a dummy PCMReader which automatically raises DecodingError

    this is to be returned by an AudioFile's to_pcm() method
    if some error occurs when initializing a decoder
    an encoder's from_pcm() method will then catch the DecodingError
    at close()-time and propogate an EncodingError"""

    def __init__(self, error_message,
                 sample_rate, channels, channel_mask, bits_per_sample):
        PCMReader.__init__(self, None, sample_rate, channels, channel_mask,
                           bits_per_sample)
        self.error_message = error_message

    def read(self, pcm_frames):
        """always returns an empty framelist"""

        return pcm.from_list([],
                             self.channels,
                             self.bits_per_sample,
                             True)

    def close(self):
        """always raises DecodingError"""

        raise DecodingError(self.error_message)


def to_pcm_progress(audiofile, progress):
    if (progress is None):
        return audiofile.to_pcm()
    else:
        return PCMReaderProgress(audiofile.to_pcm(),
                                 audiofile.total_frames(),
                                 progress)


class PCMReaderProgress:
    def __init__(self, pcmreader, total_frames, progress, current_frames=0):
        self.__read__ = pcmreader.read
        self.__close__ = pcmreader.close
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.current_frames = current_frames
        self.total_frames = total_frames
        self.progress = progress

    def read(self, pcm_frames):
        frame = self.__read__(pcm_frames)
        self.current_frames += frame.frames
        self.progress(self.current_frames, self.total_frames)
        return frame

    def close(self):
        self.__close__()


class ReorderedPCMReader:
    """a PCMReader wrapper which reorders its output channels"""

    def __init__(self, pcmreader, channel_order, channel_mask=None):
        """initialized with a PCMReader and list of channel number integers

        for example, to swap the channels of a stereo stream:
        >>> ReorderedPCMReader(reader,[1,0])

        may raise ValueError if the number of channels specified by
        channel_order doesn't match the given channel mask
        if channel mask is nonzero
        """

        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = len(channel_order)
        if (channel_mask is None):
            self.channel_mask = pcmreader.channel_mask
        else:
            self.channel_mask = channel_mask

        if ((self.channel_mask != 0) and
            (len(ChannelMask(self.channel_mask)) != self.channels)):
            #channel_mask is defined but has a different number of channels
            #than the channel count attribute
            from .text import ERR_CHANNEL_COUNT_MASK_MISMATCH
            raise ValueError(ERR_CHANNEL_COUNT_MASK_MISMATCH)
        self.bits_per_sample = pcmreader.bits_per_sample
        self.channel_order = channel_order

    def read(self, pcm_frames):
        """try to read a pcm.FrameList with the given number of frames"""

        framelist = self.pcmreader.read(pcm_frames)

        return pcm.from_channels([framelist.channel(channel)
                                  for channel in self.channel_order])

    def close(self):
        """closes the stream"""

        self.pcmreader.close()


class RemaskedPCMReader:
    """a PCMReader wrapper which changes the channel count and mask"""

    def __init__(self, pcmreader, channel_count, channel_mask):
        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = channel_count
        self.channel_mask = channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample

        if ((pcmreader.channel_mask != 0) and (channel_mask != 0)):
            #both channel masks are defined
            #so forward matching channels from pcmreader
            #and replace non-matching channels with empty samples

            mask = ChannelMask(channel_mask)
            if (len(mask) != channel_count):
                from .text import ERR_CHANNEL_COUNT_MASK_MISMATCH
                raise ValueError(ERR_CHANNEL_COUNT_MASK_MISMATCH)
            reader_channels = ChannelMask(pcmreader.channel_mask).channels()

            self.__channels__ = [(reader_channels.index(c)
                                  if c in reader_channels
                                  else None) for c in mask.channels()]
        else:
            #at least one channel mask is undefined
            #so forward up to "channel_count" channels from pcmreader
            #and replace any remainders with empty samples
            if (channel_count <= pcmreader.channels):
                self.__channels__ = range(channel_count)
            else:
                self.__channels__ = (range(channel_count) +
                                     [None] * (channel_count -
                                               pcmreader.channels))

        from .pcm import from_list,from_channels
        self.blank_channel = from_list([],
                                       1,
                                       self.pcmreader.bits_per_sample,
                                       True)
        self.from_channels = from_channels

    def read(self, pcm_frames):
        frame = self.pcmreader.read(pcm_frames)

        if (len(self.blank_channel) != frame.frames):
            #ensure blank channel is large enough
            from .pcm import from_list
            self.blank_channel = from_list([0] * frame.frames,
                                           1,
                                           self.pcmreader.bits_per_sample,
                                           True)

        return self.from_channels([(frame.channel(c)
                                    if c is not None else
                                    self.blank_channel)
                                   for c in self.__channels__])


    def close(self):
        self.pcmreader.close()


def transfer_data(from_function, to_function):
    """sends BUFFER_SIZE strings from from_function to to_function

    this continues until an empty string is returned from from_function"""

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
    """sends pcm.FrameLists from pcmreader to to_function

    frameLists are converted to strings using the signed and big_endian
    arguments.  This continues until an empty FrameLists is returned
    from pcmreader
    """

    f = pcmreader.read(FRAMELIST_SIZE)
    while (len(f) > 0):
        to_function(f.to_bytes(big_endian, signed))
        f = pcmreader.read(FRAMELIST_SIZE)


def threaded_transfer_framelist_data(pcmreader, to_function,
                                     signed=True, big_endian=False):
    """sends pcm.FrameLists from pcmreader to to_function via threads

    frameLists are converted to strings using the signed and big_endian
    arguments.  This continues until an empty FrameLists is returned
    from pcmreader.  It operates by splitting reading and writing
    into threads in the hopes that an intermittant reader
    will not disrupt the writer
    """

    import threading
    import Queue

    def send_data(pcmreader, queue):
        try:
            s = pcmreader.read(FRAMELIST_SIZE)
            while (len(s) > 0):
                queue.put(s)
                s = pcmreader.read(FRAMELIST_SIZE)
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
    """returns True if the PCM data in pcmreader1 equals pcmreader2

    the readers must be closed separately
    """

    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return False

    reader1 = BufferedPCMReader(pcmreader1)
    reader2 = BufferedPCMReader(pcmreader2)

    s1 = reader1.read(FRAMELIST_SIZE)
    s2 = reader2.read(FRAMELIST_SIZE)

    while ((len(s1) > 0) and (len(s2) > 0)):
        if (s1 != s2):
            transfer_data(reader1.read, lambda x: x)
            transfer_data(reader2.read, lambda x: x)
            return False
        else:
            s1 = reader1.read(FRAMELIST_SIZE)
            s2 = reader2.read(FRAMELIST_SIZE)

    return True


def stripped_pcm_cmp(pcmreader1, pcmreader2):
    """returns True if the stripped PCM data of pcmreader1 equals pcmreader2

    this operates by reading each PCM streams entirely to memory,
    performing strip() on their output and comparing checksums
    (which permits us to store just one big blob of memory at a time)
    """

    if ((pcmreader1.sample_rate != pcmreader2.sample_rate) or
        (pcmreader1.channels != pcmreader2.channels) or
        (pcmreader1.bits_per_sample != pcmreader2.bits_per_sample)):
        return False

    import cStringIO
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
    """returns the PCM Frame number of the first mismatch

    if the two streams match completely, returns None
    may raise IOError or ValueError if problems occur
    when reading PCM streams"""

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

    framelist1 = reader1.read(FRAMELIST_SIZE)
    framelist2 = reader2.read(FRAMELIST_SIZE)

    while ((len(framelist1) > 0) and (len(framelist2) > 0)):
        if (framelist1 != framelist2):
            for i in xrange(min(framelist1.frames, framelist2.frames)):
                if (framelist1.frame(i) != framelist2.frame(i)):
                    return frame_number + i
            else:
                return frame_number + i
        else:
            frame_number += framelist1.frames
            framelist1 = reader1.read(FRAMELIST_SIZE)
            framelist2 = reader2.read(FRAMELIST_SIZE)

    return None


class PCMCat(PCMReader):
    """a PCMReader for concatenating several PCMReaders"""

    def __init__(self, pcmreaders):
        """pcmreaders is an iterator of PCMReader objects

        note that this currently does no error checking
        to ensure reads have the same sample_rate, channels,
        bits_per_sample or channel mask!
        one must perform that check prior to building a PCMCat
        """

        self.reader_queue = pcmreaders

        try:
            self.first = self.reader_queue.next()
        except StopIteration:
            from .text import ERR_NO_PCMREADERS
            raise ValueError(ERR_NO_PCMREADERS)

        self.sample_rate = self.first.sample_rate
        self.channels = self.first.channels
        self.channel_mask = self.first.channel_mask
        self.bits_per_sample = self.first.bits_per_sample

    def read(self, pcm_frames):
        """try to read a pcm.FrameList with the given number of frames"""

        try:
            s = self.first.read(pcm_frames)
            if (len(s) > 0):
                return s
            else:
                self.first.close()
                self.first = self.reader_queue.next()
                return self.read(pcm_frames)
        except StopIteration:
            return pcm.from_list([],
                                 self.channels,
                                 self.bits_per_sample,
                                 True)

    def close(self):
        """closes the stream for reading"""

        pass


class BufferedPCMReader:
    """a PCMReader which reads exact counts of PCM frames"""

    def __init__(self, pcmreader):
        """pcmreader is a regular PCMReader object"""

        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.buffer = pcm.from_list([],
                                    self.channels,
                                    self.bits_per_sample,
                                    True)

    def close(self):
        """closes the sub-pcmreader and frees our internal buffer"""

        del(self.buffer)
        self.pcmreader.close()

    def read(self, pcm_frames):
        """reads the given number of PCM frames

        this may return fewer than the given number
        at the end of a stream
        but will never return more than requested
        """

        #fill our buffer to at least "pcm_frames", possibly more
        while (self.buffer.frames < pcm_frames):
            frame = self.pcmreader.read(FRAMELIST_SIZE)
            if (len(frame)):
                self.buffer += frame
            else:
                break

        #chop off the preceding number of PCM frames and return them
        (output, self.buffer) = self.buffer.split(pcm_frames)

        return output


class CounterPCMReader:
    """a PCMReader which counts bytes and frames written"""

    def __init__(self, pcmreader):
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample

        self.__pcmreader__ = pcmreader
        self.frames_written = 0

    def bytes_written(self):
        return (self.frames_written *
                self.channels *
                (self.bits_per_sample / 8))

    def read(self, pcm_frames):
        frame = self.__pcmreader__.read(pcm_frames)
        self.frames_written += frame.frames
        return frame

    def close(self):
        self.__pcmreader__.close()


class LimitedFileReader:
    def __init__(self, file, total_bytes):
        self.__file__ = file
        self.__total_bytes__ = total_bytes

    def read(self, x):
        if (self.__total_bytes__ > 0):
            s = self.__file__.read(x)
            if (len(s) <= self.__total_bytes__):
                self.__total_bytes__ -= len(s)
                return s
            else:
                s = s[0:self.__total_bytes__]
                self.__total_bytes__ = 0
                return s
        else:
            return ""

    def close(self):
        self.__file__.close()


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

    def read(self, pcm_frames):
        if (self.total_pcm_frames > 0):
            frame = self.pcmreader.read(min(pcm_frames, self.total_pcm_frames))
            self.total_pcm_frames -= frame.frames
            return frame
        else:
            return pcm.FrameList("", self.channels, self.bits_per_sample,
                                 False, True)

    def close(self):
        self.total_pcm_frames = 0


def pcm_split(reader, pcm_lengths):
    """yields a PCMReader object from reader for each pcm_length (in frames)

    each sub-reader is pcm_length PCM frames long with the same
    channels, bits_per_sample, sample_rate and channel_mask
    as the full stream.  reader is closed upon completion
    """

    import cStringIO
    import tempfile

    def chunk_sizes(total_size, chunk_size):
        while (total_size > chunk_size):
            total_size -= chunk_size
            yield chunk_size
        yield total_size

    full_data = BufferedPCMReader(reader)

    for pcm_length in pcm_lengths:
        if (pcm_length > (FRAMELIST_SIZE * 10)):
            #if the sub-file length is somewhat large, use a temporary file
            sub_file = tempfile.TemporaryFile()
            for size in chunk_sizes(pcm_length, FRAMELIST_SIZE):
                sub_file.write(full_data.read(size).to_bytes(False, True))
            sub_file.seek(0, 0)
        else:
            #if the sub-file length is very small, use StringIO
            sub_file = cStringIO.StringIO(
                full_data.read(pcm_length).to_bytes(False, True))

        yield PCMReader(sub_file,
                        reader.sample_rate,
                        reader.channels,
                        reader.channel_mask,
                        reader.bits_per_sample)

    full_data.close()


def PCMConverter(pcmreader,
                 sample_rate,
                 channels,
                 channel_mask,
                 bits_per_sample):
    """a PCMReader wrapper for converting attributes

    for example, this can be used to alter sample_rate, bits_per_sample,
    channel_mask, channel count, or any combination of those
    attributes.  It resamples, downsamples, etc. to achieve the proper
    output

    may raise ValueError if any of the attributes are unsupported
    or invalid
    """

    if (sample_rate <= 0):
        from .text import ERR_INVALID_SAMPLE_RATE
        raise ValueError(ERR_INVALID_SAMPLE_RATE)
    elif (channels <= 0):
        from .text import ERR_INVALID_CHANNEL_COUNT
        raise ValueError(ERR_INVALID_CHANNEL_COUNT)
    elif (bits_per_sample not in (8, 16, 24)):
        from .text import ERR_INVALID_BITS_PER_SAMPLE
        raise ValueError(ERR_INVALID_BITS_PER_SAMPLE)

    if ((channel_mask != 0) and (len(ChannelMask(channel_mask)) != channels)):
        #channel_mask is defined but has a different number of channels
        #than the channel count attribute
        from .text import ERR_CHANNEL_COUNT_MASK_MISMATCH
        raise ValueError(ERR_CHANNEL_COUNT_MASK_MISMATCH)

    if (pcmreader.channels > channels):
        if ((channels == 1) and (channel_mask in (0, 0x4))):
            if (pcmreader.channels > 2):
                #reduce channel count through downmixing
                #followed by averaging
                from .pcmconverter import Averager,Downmixer
                pcmreader = Averager(Downmixer(pcmreader))
            else:
                #pcmreader.channels == 2
                #so reduce channel count through averaging
                from .pcmconverter import Averager
                pcmreader = Averager(pcmreader)
        elif ((channels == 2) and (channel_mask in (0, 0x3))):
            #reduce channel count through downmixing
            from .pcmconverter import Downmixer
            pcmreader = Downmixer(pcmreader)
        else:
            #unusual channel count/mask combination
            pcmreader = RemaskedPCMReader(pcmreader,
                                          channels,
                                          channel_mask)
    elif (pcmreader.channels < channels):
        #increase channel count by duplicating first channel
        #(this is usually just going from mono to stereo
        # since there's no way to summon surround channels
        # out of thin air)
        pcmreader = ReorderedPCMReader(pcmreader,
                                       range(pcmreader.channels) +
                                       [0] * (channels - pcmreader.channels),
                                       channel_mask)

    if (pcmreader.sample_rate != sample_rate):
        #convert sample rate through resampling
        from .pcmconverter import Resampler
        pcmreader = Resampler(pcmreader, sample_rate)

    if (pcmreader.bits_per_sample != bits_per_sample):
        #use bitshifts/dithering to adjust bits-per-sample
        from .pcmconverter import BPSConverter
        pcmreader = BPSConverter(pcmreader, bits_per_sample)

    return pcmreader


def resampled_frame_count(initial_frame_count,
                          initial_sample_rate,
                          new_sample_rate):
    """given an initial PCM frame count, initial sample rate
    and new sample rate, returns the new PCM frame count
    once the stream has been resampled"""

    if (initial_sample_rate == new_sample_rate):
        return initial_frame_count
    else:
        from decimal import Decimal,ROUND_DOWN
        new_frame_count = ((Decimal(initial_frame_count) *
                            Decimal(new_sample_rate)) /
                           Decimal(initial_sample_rate))
        return int(new_frame_count.quantize(
                Decimal("1."), rounding=ROUND_DOWN))


def applicable_replay_gain(tracks):
    """returns True if ReplayGain can be applied to a list of AudioFiles

    this checks their sample rate and channel count to determine
    applicability"""

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


def calculate_replay_gain(tracks, progress=None):
    """yields (track, track_gain, track_peak, album_gain, album_peak)
    for each AudioFile in the list of tracks

    raises ValueError if a problem occurs during calculation"""

    if (len(tracks) == 0):
        return

    from . import replaygain as replaygain
    from bisect import bisect

    SUPPORTED_RATES = [8000,  11025,  12000,  16000,  18900,  22050, 24000,
                       32000, 37800,  44100,  48000,  56000,  64000, 88200,
                       96000, 112000, 128000, 144000, 176400, 192000]

    target_rate = ([SUPPORTED_RATES[0]] + SUPPORTED_RATES)[
        bisect(SUPPORTED_RATES, most_numerous([track.sample_rate()
                                               for track in tracks]))]

    track_frames = [resampled_frame_count(track.total_frames(),
                                          track.sample_rate(),
                                          target_rate)
                    for track in tracks]
    current_frames = 0
    total_frames = sum(track_frames)

    rg = replaygain.ReplayGain(target_rate)

    gains = []

    for (track, track_frames) in zip(tracks, track_frames):
        pcm = track.to_pcm()

        if (pcm.channels > 2):
            #add a wrapper to cull any channels above 2
            output_channels = 2
            output_channel_mask = 0x3
        else:
            output_channels = pcm.channels
            output_channel_mask = pcm.channel_mask

        if ((pcm.channels != output_channels) or
            (pcm.channel_mask != output_channel_mask) or
            (pcm.sample_rate) != target_rate):
            pcm = PCMConverter(pcm,
                               target_rate,
                               output_channels,
                               output_channel_mask,
                               pcm.bits_per_sample)

        #finally, perform the gain calculation on the PCMReader
        #and accumulate the title gain
        if (progress is not None):
            (track_gain, track_peak) = rg.title_gain(
                PCMReaderProgress(pcm, total_frames, progress,
                                  current_frames=current_frames))
            current_frames += track_frames
        else:
            (track_gain, track_peak) = rg.title_gain(pcm)
        gains.append((track, track_gain, track_peak))

    #once everything is calculated, get the album gain
    (album_gain, album_peak) = rg.album_gain()

    #yield a set of accumulated track and album gains
    for (track, track_gain, track_peak) in gains:
        yield (track, track_gain, track_peak, album_gain, album_peak)


def ignore_sigint():
    """sets the SIGINT signal to SIG_IGN

    some encoder executables require this in order for
    interruptableReader to work correctly since we
    want to catch SIGINT ourselves in that case and perform
    a proper shutdown"""

    import signal

    signal.signal(signal.SIGINT, signal.SIG_IGN)


def make_dirs(destination_path):
    """ensures all directories leading to destination_path are created

    raises OSError if a problem occurs during directory creation
    """

    dirname = os.path.dirname(destination_path)
    if ((dirname != '') and (not os.path.isdir(dirname))):
        os.makedirs(dirname)


#######################
#Generic MetaData
#######################


class MetaData:
    """the base class for storing textual AudioFile metadata

    Fields may be None, indicating they're not present
    in the underlying metadata implementation.

    Changing a field to a new value will update the underlying metadata
    (e.g. vorbiscomment.track_name = u"Foo"
    will set a Vorbis comment's "TITLE" field to "Foo")

    Updating the underlying metadata will change the metadata's fields
    (e.g. setting a Vorbis comment's "TITLE" field to "bar"
    will update vorbiscomment.title_name to u"bar")

    Deleting a field or setting it to None
    will remove it from the underlying metadata
    (e.g. del(vorbiscomment.track_name) will delete the "TITLE" field)
    """

    FIELDS = ("track_name",
              "track_number",
              "track_total",
              "album_name",
              "artist_name",
              "performer_name",
              "composer_name",
              "conductor_name",
              "media",
              "ISRC",
              "catalog",
              "copyright",
              "publisher",
              "year",
              "date",
              "album_number",
              "album_total",
              "comment")

    INTEGER_FIELDS = ("track_number",
                      "track_total",
                      "album_number",
                      "album_total")

    #this is the order fields should be presented to the user
    #to ensure consistency across utilities
    FIELD_ORDER = ("track_name",
                   "artist_name",
                   "album_name",
                   "track_number",
                   "track_total",
                   "album_number",
                   "album_total",
                   "performer_name",
                   "composer_name",
                   "conductor_name",
                   "catalog",
                   "ISRC",
                   "publisher",
                   "media",
                   "year",
                   "date",
                   "copyright",
                   "comment")

    #this is the name fields should use when presented to the user
    #also to ensure constency across utilities
    from .text import (METADATA_TRACK_NAME,
                       METADATA_TRACK_NUMBER,
                       METADATA_TRACK_TOTAL,
                       METADATA_ALBUM_NAME,
                       METADATA_ARTIST_NAME,
                       METADATA_PERFORMER_NAME,
                       METADATA_COMPOSER_NAME,
                       METADATA_CONDUCTOR_NAME,
                       METADATA_MEDIA,
                       METADATA_ISRC,
                       METADATA_CATALOG,
                       METADATA_COPYRIGHT,
                       METADATA_PUBLISHER,
                       METADATA_YEAR,
                       METADATA_DATE,
                       METADATA_ALBUM_NUMBER,
                       METADATA_ALBUM_TOTAL,
                       METADATA_COMMENT)

    FIELD_NAMES = {"track_name":METADATA_TRACK_NAME,
                   "track_number":METADATA_TRACK_NUMBER,
                   "track_total":METADATA_TRACK_TOTAL,
                   "album_name":METADATA_ALBUM_NAME,
                   "artist_name":METADATA_ARTIST_NAME,
                   "performer_name":METADATA_PERFORMER_NAME,
                   "composer_name":METADATA_COMPOSER_NAME,
                   "conductor_name":METADATA_CONDUCTOR_NAME,
                   "media":METADATA_MEDIA,
                   "ISRC":METADATA_ISRC,
                   "catalog":METADATA_CATALOG,
                   "copyright":METADATA_COPYRIGHT,
                   "publisher":METADATA_PUBLISHER,
                   "year":METADATA_YEAR,
                   "date":METADATA_DATE,
                   "album_number":METADATA_ALBUM_NUMBER,
                   "album_total":METADATA_ALBUM_TOTAL,
                   "comment":METADATA_COMMENT}

    def __init__(self,
                 track_name=None,
                 track_number=None,
                 track_total=None,
                 album_name=None,
                 artist_name=None,
                 performer_name=None,
                 composer_name=None,
                 conductor_name=None,
                 media=None,
                 ISRC=None,
                 catalog=None,
                 copyright=None,
                 publisher=None,
                 year=None,
                 date=None,
                 album_number=None,
                 album_total=None,
                 comment=None,
                 images=None):
        """
| field          | type    | meaning                              |
|----------------+---------+--------------------------------------|
| track_name     | unicode | the name of this individual track    |
| track_number   | integer | the number of this track             |
| track_total    | integer | the total number of tracks           |
| album_name     | unicode | the name of this track's album       |
| artist_name    | unicode | the song's original creator/composer |
| performer_name | unicode | the song's performing artist         |
| composer_name  | unicode | the song's composer name             |
| conductor_name | unicode | the song's conductor's name          |
| media          | unicode | the album's media type               |
| ISRC           | unicode | the song's ISRC                      |
| catalog        | unicode | the album's catalog number           |
| copyright      | unicode | the song's copyright information     |
| publisher      | unicode | the album's publisher                |
| year           | unicode | the album's release year             |
| date           | unicode | the original recording date          |
| album_number   | integer | the disc's volume number             |
| album_total    | integer | the total number of discs            |
| comment        | unicode | the track's comment string           |
| images         | list    | list of Image objects                |
|----------------+---------+--------------------------------------|
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
                ",".join(["%s"] * (len(MetaData.FIELDS))))) % \
                tuple(["%s=%s" % (field, repr(getattr(self, field)))
                       for field in MetaData.FIELDS])

    def __delattr__(self, field):
        if (field in self.FIELDS):
            self.__dict__[field] = None
        else:
            try:
                del(self.__dict__[field])
            except KeyError:
                raise AttributeError(field)

    def fields(self):
        """yields an (attr, value) tuple per MetaData field"""

        for attr in self.FIELDS:
            yield (attr, getattr(self, attr))

    def filled_fields(self):
        """yields an (attr, value) tuple per MetaData field
        which is not blank"""

        for (attr, field) in self.fields():
            if (field is not None):
                yield (attr, field)

    def empty_fields(self):
        """yields an (attr, value) tuple per MetaData field
        which is blank"""

        for (attr, field) in self.fields():
            if (field is None):
                yield (attr, field)

    def __unicode__(self):
        comment_pairs = []

        for attr in self.FIELD_ORDER:
            if (attr == "track_number"):
                #combine track number/track total into single field
                track_number = self.track_number
                track_total = self.track_total
                if ((track_number is None) and (track_total is None)):
                    #nothing to display
                    pass
                elif ((track_number is not None) and (track_total is None)):
                    comment_pairs.append(
                        (display_unicode(self.FIELD_NAMES[attr]),
                         unicode(track_number)))
                elif ((track_number is None) and (track_total is not None)):
                    comment_pairs.append(
                        (display_unicode(self.FIELD_NAMES[attr]),
                         u"?/%d" % (track_total,)))
                else:
                    #neither track_number or track_total is None
                    comment_pairs.append(
                        (display_unicode(self.FIELD_NAMES[attr]),
                         u"%d/%d" % (track_number, track_total)))
            elif (attr == "track_total"):
                pass
            elif (attr == "album_number"):
                #combine album number/album total into single field
                album_number = self.album_number
                album_total = self.album_total
                if ((album_number is None) and (album_total is None)):
                    #nothing to display
                    pass
                elif ((album_number is not None) and (album_total is None)):
                    comment_pairs.append(
                        (display_unicode(self.FIELD_NAMES[attr]),
                         unicode(album_number)))
                elif ((album_number is None) and (album_total is not None)):
                    comment_pairs.append(
                        (display_unicode(self.FIELD_NAMES[attr]),
                         u"?/%d" % (album_total,)))
                else:
                    #neither album_number or album_total is None
                    comment_pairs.append(
                        (display_unicode(self.FIELD_NAMES[attr]),
                         u"%d/%d" % (album_number, album_total)))
            elif (attr == "album_total"):
                pass
            elif (getattr(self, attr) is not None):
                comment_pairs.append((display_unicode(self.FIELD_NAMES[attr]),
                                      getattr(self, attr)))

        #append image data, if necessary
        from .text import LAB_PICTURE

        for image in self.images():
            comment_pairs.append((display_unicode(LAB_PICTURE),
                                  unicode(image)))

        #right-align the comment key values
        #and turn them into unicode strings
        #before returning the completed comment
        if (len(comment_pairs) > 0):
            field_len = max([len(field) for (field, value) in comment_pairs])
            return os.linesep.decode('ascii').join(
                [u"%s%s : %s" % (u" " * (field_len - len(field)),
                                 field, value)
                 for (field, value) in comment_pairs])
        else:
            return u""

    def raw_info(self):
        """returns a Unicode string of low-level MetaData information

        whereas __unicode__ is meant to contain complete information
        at a very high level
        raw_info() should be more developer-specific and with
        very little adjustment or reordering to the data itself
        """

        raise NotImplementedError()

    def __eq__(self, metadata):
        for attr in MetaData.FIELDS:
            if ((not hasattr(metadata, attr)) or
                (getattr(self, attr) != getattr(metadata, attr))):
                return False
        else:
            return True

    def __ne__(self, metadata):
        return not self.__eq__(metadata)

    @classmethod
    def converted(cls, metadata):
        """converts metadata from another class to this one, if necessary

        takes a MetaData-compatible object (or None)
        and returns a new MetaData subclass with the data fields converted
        or None if metadata is None or conversion isn't possible
        for instance, VorbisComment.converted() returns a VorbisComment
        class.  This way, AudioFiles can offload metadata conversions
        """

        if (metadata is not None):
            fields = dict([(field, getattr(metadata, field))
                           for field in cls.FIELDS])
            fields["images"] = metadata.images()
            return MetaData(**fields)
        else:
            return None

    @classmethod
    def supports_images(cls):
        """returns True if this MetaData class supports embedded images"""

        return True

    def images(self):
        """returns a list of embedded Image objects"""

        #must return a copy of our internal array
        #otherwise this will likely not act as expected when deleting
        return self.__images__[:]

    def front_covers(self):
        """returns a subset of images() which are front covers"""

        return [i for i in self.images() if i.type == 0]

    def back_covers(self):
        """returns a subset of images() which are back covers"""

        return [i for i in self.images() if i.type == 1]

    def leaflet_pages(self):
        """returns a subset of images() which are leaflet pages"""

        return [i for i in self.images() if i.type == 2]

    def media_images(self):
        """returns a subset of images() which are media images"""

        return [i for i in self.images() if i.type == 3]

    def other_images(self):
        """returns a subset of images() which are other images"""

        return [i for i in self.images() if i.type == 4]

    def add_image(self, image):
        """embeds an Image object in this metadata

        implementations of this method should also affect
        the underlying metadata value
        (e.g. adding a new Image to FlacMetaData should add another
        METADATA_BLOCK_PICTURE block to the metadata)
        """

        if (self.supports_images()):
            self.__images__.append(image)
        else:
            from .text import ERR_PICTURES_UNSUPPORTED
            raise ValueError(ERR_PICTURES_UNSUPPORTED)

    def delete_image(self, image):
        """deletes an Image object from this metadata

        implementations of this method should also affect
        the underlying metadata value
        (e.g. removing an existing Image from FlacMetaData should
        remove that same METADATA_BLOCK_PICTURE block from the metadata)
        """

        if (self.supports_images()):
            self.__images__.pop(self.__images__.index(image))
        else:
            from .text import ERR_PICTURES_UNSUPPORTED
            raise ValueError(ERR_PICTURES_UNSUPPORTED)

    def clean(self, fixes_performed):
        """returns a new MetaData object that's been cleaned of problems

        any fixes performed are appended to fixes_performed as Unicode
        fixes to apply to metadata include:
        * Remove leading or trailing whitespace from text fields
        * Remove empty fields
        * Remove leading zeroes from numerical fields
          (except when requested, in the case of ID3v2)
        * Fix incorrectly labeled image metadata fields
        """

        return self


class AlbumMetaData(dict):
    """a container for several MetaData objects

    they can be retrieved by track number"""

    def __init__(self, metadata_iter):
        """metadata_iter is an iterator of MetaData objects"""

        dict.__init__(self,
                      dict([(m.track_number, m) for m in metadata_iter]))

    def metadata(self):
        """returns a single MetaData object of all consistent fields

        for example, if album_name is the same in all MetaData objects,
        the returned object will have that album_name value
        if track_name differs, the returned object will not
        have a track_name field
        """

        return MetaData(**dict([(field, list(items)[0])
                                for (field, items) in
                                [(field,
                                  set([getattr(track, field) for track
                                       in self.values()]))
                                 for field in MetaData.FIELDS]
                                if (len(items) == 1)]))


#######################
#Image MetaData
#######################


class Image:
    """an image data container"""

    def __init__(self, data, mime_type, width, height,
                 color_depth, color_count, description, type):
        """fields are as follows:

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
        """returns the image's recommended suffix as a plain string

        for example, an image with mime_type "image/jpeg" return "jpg"
        """

        return {"image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/gif": "gif",
                "image/png": "png",
                "image/x-ms-bmp": "bmp",
                "image/tiff": "tiff"}.get(self.mime_type, "bin")

    def type_string(self):
        """returns the image's type as a human readable plain string

        for example, an image of type 0 returns "Front Cover"
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
        return u"%s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width, self.height, self.mime_type)

    @classmethod
    def new(cls, image_data, description, type):
        """builds a new Image object from raw data

        image_data is a plain string of binary image data
        description is a unicode string
        type as an image type integer

        the width, height, color_depth and color_count fields
        are determined by parsing the binary image data
        raises InvalidImage if some error occurs during parsing
        """

        from .image import image_metrics

        img = image_metrics(image_data)

        return Image(data=image_data,
                     mime_type=img.mime_type,
                     width=img.width,
                     height=img.height,
                     color_depth=img.bits_per_pixel,
                     color_count=img.color_count,
                     description=description,
                     type=type)

    def __eq__(self, image):
        if (image is not None):
            for attr in ["data", "mime_type", "width", "height",
                         "color_depth", "color_count", "description",
                         "type"]:
                if ((not hasattr(image, attr)) or
                    (getattr(self, attr) != getattr(image, attr))):
                    return False
            else:
                return True
        else:
            return False

    def __ne__(self, image):
        return not self.__eq__(image)


class InvalidImage(Exception):
    """raised if an image cannot be parsed correctly"""

    def __init__(self, err):
        self.err = unicode(err)

    def __unicode__(self):
        return self.err


#######################
#ReplayGain Metadata
#######################


class ReplayGain:
    """a container for ReplayGain data"""

    def __init__(self, track_gain, track_peak, album_gain, album_peak):
        """values are:

        track_gain - a dB float value
        track_peak - the highest absolute value PCM sample, as a float
        album_gain - a dB float value
        album_peak - the highest absolute value PCM sample, as a float

        they are also attributes
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
        from operator import and_

        return reduce(and_,
                      [(hasattr(rg, attr) and
                        (getattr(self, attr) == getattr(rg, attr)))
                       for attr in ["track_gain", "track_peak",
                                    "album_gain", "album_peak"]])

    def __ne__(self, rg):
        return not self.__eq__(rg)


#######################
#Generic Audio File
#######################

class UnsupportedTracknameField(Exception):
    """raised by AudioFile.track_name()
    if its format string contains unknown fields"""

    def __init__(self, field):
        self.field = field

    def error_msg(self, messenger):
        from .text import (ERR_UNKNOWN_FIELD,
                           LAB_SUPPORTED_FIELDS)

        messenger.error(ERR_UNKNOWN_FIELD % (self.field,))
        messenger.info(LAB_SUPPORTED_FIELDS)
        for field in sorted(MetaData.FIELDS + \
                            ("album_track_number", "suffix")):
            if (field == 'track_number'):
                messenger.info(u"%(track_number)2.2d")
            else:
                messenger.info(u"%%(%s)s" % (field))

        messenger.info(u"%(basename)s")

class InvalidFilenameFormat(Exception):
    """raised by AudioFile.track_name()
    if its format string contains broken fields"""

    def __unicode__(self):
        from .text import ERR_INVALID_FILENAME_FORMAT
        return ERR_INVALID_FILENAME_FORMAT


class AudioFile:
    """an abstract class representing audio files on disk

    this class should be extended to handle different audio
    file formats"""

    SUFFIX = ""
    NAME = ""
    DESCRIPTION = u""
    DEFAULT_COMPRESSION = ""
    COMPRESSION_MODES = ("",)
    COMPRESSION_DESCRIPTIONS = {}
    BINARIES = tuple()
    REPLAYGAIN_BINARIES = tuple()

    def __init__(self, filename):
        """filename is a plain string

        raises InvalidFile or subclass if the file is invalid in some way"""

        self.filename = filename

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        raise NotImplementedError()

    def channels(self):
        """returns an integer number of channels this track contains"""

        raise NotImplementedError()

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        #WARNING - This only returns valid masks for 1 and 2 channel audio
        #anything over 2 channels raises a ValueError
        #since there isn't any standard on what those channels should be.
        #AudioFiles that support more than 2 channels should override
        #this method with one that returns the proper mask.
        return ChannelMask.from_channels(self.channels())

    def lossless(self):
        """returns True if this track's data is stored losslessly"""

        raise NotImplementedError()

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        #this is a sort of low-level implementation
        #which assumes higher-level routines have
        #modified metadata properly

        if (metadata is not None):
            raise NotImplementedError()
        else:
            raise ValueError(ERR_FOREIGN_METADATA)

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        #this is a higher-level implementation
        #which assumes metadata is from a different audio file
        #or constructed from scratch and converts it accordingly
        #before passing it on to update_metadata()

        pass

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        return None

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        pass

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        raise NotImplementedError()

    def cd_frames(self):
        """returns the total length of the track in CD frames

        each CD frame is 1/75th of a second"""

        try:
            return (self.total_frames() * 75) / self.sample_rate()
        except ZeroDivisionError:
            return 0

    def seconds_length(self):
        """returns the length of the track as a Decimal number of seconds"""

        import decimal

        try:
            return (decimal.Decimal(self.total_frames()) /
                    decimal.Decimal(self.sample_rate()))
        except decimal.DivisionByZero:
            return decimal.Decimal(0)

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        raise NotImplementedError()

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data

        if an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message"""

        raise NotImplementedError()

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AudioFile-compatible object

        for example, to encode the FlacAudio file "file.flac" from "file.wav"
        at compression level "5":

        >>> flac = FlacAudio.from_pcm("file.flac",
        ...                           WaveAudio("file.wav").to_pcm(),
        ...                           "5")

        may raise EncodingError if some problem occurs when
        encoding the input file.  This includes an error
        in the input stream, a problem writing the output file,
        or even an EncodingError subclass such as
        "UnsupportedBitsPerSample" if the input stream
        is formatted in a way this class is unable to support
        """

        raise NotImplementedError()

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """encodes a new AudioFile from existing AudioFile

        take a filename string, target class and optional compression string
        encodes a new AudioFile in the target class and returns
        the resulting object
        may raise EncodingError if some problem occurs during encoding"""

        return target_class.from_pcm(target_path,
                                     to_pcm_progress(self, progress),
                                     compression)

    @classmethod
    def __unlink__(cls, filename):
        try:
            os.unlink(filename)
        except OSError:
            pass

    def track_number(self):
        """returns this track's number as an integer

        this first checks MetaData and then makes a guess from the filename
        if neither yields a good result, returns None"""

        metadata = self.get_metadata()
        if (metadata is not None):
            return metadata.track_number
        else:
            try:
                return int(re.findall(
                        r'\d{2,3}',
                        os.path.basename(self.filename))[0]) % 100
            except IndexError:
                return None

    def album_number(self):
        """returns this track's album number as an integer

        this first checks MetaData and then makes a guess from the filename
        if neither yields a good result, returns 0"""

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
                return None

    @classmethod
    def track_name(cls, file_path, track_metadata=None, format=None,
                   suffix=None):
        """constructs a new filename string

        given a plain string to an existing path,
        a MetaData-compatible object (or None),
        a UTF-8-encoded Python format string
        and an ASCII-encoded suffix string (such as "mp3")
        returns a plain string of a new filename with format's
        fields filled-in and encoded as FS_ENCODING

        raises UnsupportedTracknameField if the format string
        contains invalid template fields

        raises InvalidFilenameFormat if the format string
        has broken template fields"""

        if (format is None):
            format = FILENAME_FORMAT
        if (suffix is None):
            suffix = cls.SUFFIX
        try:
            #prefer track_number and album_number from MetaData, if available
            if (track_metadata is not None):
                track_number = (track_metadata.track_number
                                if track_metadata.track_number is not None
                                else 0)
                album_number = (track_metadata.album_number
                                if track_metadata.album_number is not None
                                else 0)
                track_total = (track_metadata.track_total
                               if track_metadata.track_total is not None
                               else 0)
                album_total = (track_metadata.album_total
                               if track_metadata.album_total is not None
                               else 0)
            else:
                try:
                    track_number = int(re.findall(
                            r'\d{2,4}',
                            os.path.basename(file_path))[0]) % 100
                except IndexError:
                    track_number = 0

                try:
                    album_number = int(re.findall(
                            r'\d{2,4}',
                            os.path.basename(file_path))[0]) / 100
                except IndexError:
                    album_number = 0

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
                for field in track_metadata.FIELDS:
                    if ((field != "suffix") and
                        (field not in MetaData.INTEGER_FIELDS)):
                        if (getattr(track_metadata, field) is not None):
                            format_dict[field.decode('ascii')] = getattr(
                                track_metadata,
                                field).replace(u'/',
                                               u'-').replace(unichr(0),
                                                             u' ')
                        else:
                            format_dict[field.decode('ascii')] = u""
            else:
                for field in MetaData.FIELDS:
                    if (field not in MetaData.INTEGER_FIELDS):
                        format_dict[field.decode('ascii')] = u""

            format_dict[u"basename"] = os.path.splitext(
                os.path.basename(file_path))[0].decode(FS_ENCODING,
                                                       'replace')

            return (format.decode('utf-8', 'replace') % format_dict).encode(
                FS_ENCODING, 'replace')
        except KeyError, error:
            raise UnsupportedTracknameField(unicode(error.args[0]))
        except TypeError:
            raise InvalidFilenameFormat()
        except ValueError:
            raise InvalidFilenameFormat()

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return False

    @classmethod
    def add_replay_gain(cls, filenames, progress=None):
        """adds ReplayGain values to a list of filename strings

        raises ValueError if some problem occurs during ReplayGain application
        """

        return

    @classmethod
    def can_add_replay_gain(cls, audiofiles):
        """given a list of audiofiles,
        returns True if this class can add ReplayGain to those files
        returns False if not"""

        return False

    @classmethod
    def lossless_replay_gain(cls):
        """returns True of applying ReplayGain is a lossless process

        for example, if it is applied by adding metadata tags
        rather than altering the file's data itself"""

        return False

    def replay_gain(self):
        """returns a ReplayGain object of our ReplayGain values

        returns None if we have no values
        note that if applying ReplayGain is a lossy process,
        this will typically also return None"""

        return None

    def set_cuesheet(self, cuesheet):
        """imports cuesheet data from a Cuesheet-compatible object

        this are objects with catalog(), ISRCs(), indexes(), and pcm_lengths()
        methods.  Raises IOError if an error occurs setting the cuesheet"""

        pass

    def get_cuesheet(self):
        """returns the embedded Cuesheet-compatible object, or None

        raises IOError if a problem occurs when reading the file"""

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

    def verify(self, progress=None):
        """verifies the current file for correctness

        returns True if the file is okay
        raises an InvalidFile with an error message if there is
        some problem with the file"""

        total_frames = self.total_frames()
        decoder = self.to_pcm()
        pcm_frame_count = 0
        try:
            framelist = decoder.read(FRAMELIST_SIZE)
            while (len(framelist) > 0):
                pcm_frame_count += framelist.frames
                if (progress is not None):
                    progress(pcm_frame_count, total_frames)
                framelist = decoder.read(FRAMELIST_SIZE)
        except (IOError, ValueError), err:
            raise InvalidFile(str(err))

        try:
            decoder.close()
        except DecodingError, err:
            raise InvalidFile(err.error_message)

        if (pcm_frame_count == total_frames):
            return True
        else:
            raise InvalidFile("incorrect PCM frame count")

    @classmethod
    def has_binaries(cls, system_binaries):
        """returns True if all the required binaries can be found

        checks the __system_binaries__ class for which path to check"""

        for command in cls.BINARIES:
            if (not system_binaries.can_execute(system_binaries[command])):
                return False
        else:
            return True

    def clean(self, fixes_performed, output_filename=None):
        """cleans the file of known data and metadata problems

        fixes_performed is a list-like object which is appended
        with Unicode strings of fixed problems

        output_filename is an optional filename of the fixed file
        if present, a new AudioFile is returned
        otherwise, only a dry-run is performed and no new file is written

        raises IOError if unable to write the file or its metadata
        raises ValueError if the file has errors of some sort
        """

        if (output_filename is None):
            #dry run only
            metadata = self.get_metadata()
            if (metadata is not None):
                metadata.clean(fixes_performed)
        else:
            #perform full fix
            input_f = file(self.filename, "rb")
            output_f = file(output_filename, "wb")
            try:
                transfer_data(input_f.read, output_f.write)
            finally:
                input_f.close()
                output_f.close()

            new_track = open(output_filename)
            metadata = self.get_metadata()
            if (metadata is not None):
                new_track.set_metadata(metadata.clean(fixes_performed))
            return new_track


class WaveContainer(AudioFile):
    def has_foreign_wave_chunks(self):
        """returns True if the file has RIFF chunks
        other than 'fmt ' and 'data'
        which must be preserved during conversion"""

        raise NotImplementedError()

    def wave_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        if self.has_foreign_wave_chunks() is False,
        may raise ValueError if the file has no header and footer
        for any reason"""

        raise NotImplementedError()

    @classmethod
    def from_wave(cls, filename, header, pcmreader, footer, compression=None):
        """encodes a new file from wave data

        takes a filename string, header string,
        PCMReader object, footer string
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new WaveAudio object

        header + pcm data + footer should always result
        in the original wave file being restored
        without need for any padding bytes

        may raise EncodingError if some problem occurs when
        encoding the input file"""

        raise NotImplementedError()

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """encodes a new AudioFile from existing AudioFile

        take a filename string, target class and optional compression string
        encodes a new AudioFile in the target class and returns
        the resulting object
        may raise EncodingError if some problem occurs during encoding"""

        if (self.has_foreign_wave_chunks() and
            hasattr(target_class, "from_wave") and
            callable(target_class.from_wave)):
            #transfer header and footer when performing PCM conversion
            (header, footer) = self.wave_header_footer()
            return target_class.from_wave(target_path,
                                          header,
                                          to_pcm_progress(self, progress),
                                          footer,
                                          compression)
        else:
            #perform standard PCM conversion instead
            return target_class.from_pcm(target_path,
                                         to_pcm_progress(self, progress),
                                         compression)


class AiffContainer(AudioFile):
    def has_foreign_aiff_chunks(self):
        """returns True if the file has AIFF chunks
        other than 'COMM' and 'SSND'
        which must be preserved during conversion"""

        raise NotImplementedError()

    def aiff_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        if self.has_foreign_aiff_chunks() is False,
        may raise ValueError if the file has no header and footer
        for any reason"""

        raise NotImplementedError()

    @classmethod
    def from_aiff(cls, filename, header, pcmreader, footer, compression=None):
        """encodes a new file from AIFF data

        takes a filename string, header string,
        PCMReader object, footer string
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AiffAudio object

        header + pcm data + footer should always result
        in the original AIFF file being restored
        without need for any padding bytes

        may raise EncodingError if some problem occurs when
        encoding the input file"""

        raise NotImplementedError()

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """encodes a new AudioFile from existing AudioFile

        take a filename string, target class and optional compression string
        encodes a new AudioFile in the target class and returns
        the resulting object
        may raise EncodingError if some problem occurs during encoding"""

        if (self.has_foreign_aiff_chunks() and
            hasattr(target_class, "from_aiff") and
            callable(target_class.from_aiff)):
            #transfer header and footer when performing PCM conversion
            (header, footer) = self.aiff_header_footer()
            return target_class.from_aiff(target_path,
                                          header,
                                          to_pcm_progress(self, progress),
                                          footer,
                                          compression)
        else:
            #perform standard PCM conversion instead
            return target_class.from_pcm(target_path,
                                         to_pcm_progress(self, progress),
                                         compression)


class DummyAudioFile(AudioFile):
    """a placeholder AudioFile object with external data"""

    def __init__(self, length, metadata, track_number=0):
        """fields are as follows:

        length       - the dummy track's length, in CD frames
        metadata     - a MetaData object
        track_number - the track's number on CD, starting from 1
        """

        self.__length__ = length
        self.__metadata__ = metadata
        self.__track_number__ = track_number

        AudioFile.__init__(self, "")

    def get_metadata(self):
        """returns a MetaData object, or None"""

        return self.__metadata__

    def cd_frames(self):
        """returns the total length of the track in CD frames

        each CD frame is 1/75th of a second"""

        return self.__length__

    def track_number(self):
        """returns this track's number as an integer"""

        return self.__track_number__

    def sample_rate(self):
        """returns 44100"""

        return 44100

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return (self.cd_frames() * self.sample_rate()) / 75

###########################
#Cuesheet/TOC file handling
###########################

#Cuesheets and TOC files are bundled into a unified Sheet interface


class SheetException(ValueError):
    """a parent exception for CueException and TOCException"""

    pass


def read_sheet(filename):
    """returns a TOCFile or Cuesheet object from filename

    may raise a SheetException if the file cannot be parsed correctly"""

    import toc
    import cue

    try:
        #try TOC first, since its CD_DA header makes it easier to spot
        return toc.read_tocfile(filename)
    except SheetException:
        return cue.read_cuesheet(filename)


def parse_timestamp(s):
    """parses a timestamp string into an integer

    this presumes the stamp is stored: "hours:minutes:frames"
    where each CD frame is 1/75th of a second
    or, if the stamp is a plain integer, it is returned directly
    this does no error checking.  Presumably a regex will ensure
    the stamp is formatted correctly before parsing it to an int
    """

    if (":" in s):
        (m, s, f) = map(int, s.split(":"))
        return (m * 60 * 75) + (s * 75) + f
    else:
        return int(s)


def build_timestamp(i):
    """returns a timestamp string from an integer number of CD frames

    each CD frame is 1/75th of a second
    """

    return "%2.2d:%2.2d:%2.2d" % ((i / 75) / 60, (i / 75) % 60, i % 75)


def at_a_time(total, per):
    """yields "per" integers from "total" until exhausted

    for example:
    >>> list(at_a_time(10, 3))
    [3, 3, 3, 1]
    """

    for i in xrange(total / per):
        yield per
    yield total % per


def iter_first(iterator):
    """yields a (is_last, item) per item in the iterator

    where is_first indicates whether the item is the first one

    if the iterator has no items, yields (True, None)
    """

    try:
        first_item = iterator.next()
    except StopIteration:
        yield (True, None)
        return

    yield (True, first_item)

    while (True):
        try:
            yield (False, iterator.next())
        except StopIteration:
            return


def iter_last(iterator):
    """yields a (is_last, item) per item in the iterator

    where is_last indicates whether the item is the final one

    if the iterator has no items, yields (True, None)
    """

    try:
        cached_item = iterator.next()
    except StopIteration:
        yield (True, None)
        return

    while (True):
        try:
            next_item = iterator.next()
            yield (False, cached_item)
            cached_item = next_item
        except StopIteration:
            yield (True, cached_item)
            return


#######################
#CD data
#######################

#keep in mind the whole of CD reading isn't remotely thread-safe
#due to the linear nature of CD access,
#reading from more than one track of a given CD at the same time
#is something code should avoid at all costs!
#there's simply no way to accomplish that cleanly

class CDDA:
    """a CDDA device which contains CDTrackReader objects"""

    def __init__(self, device_name, speed=None, perform_logging=True):
        """device_name is a string, speed is an optional int"""

        from audiotools.cdio import identify_cdrom, CDImage, CDDA, CD_IMAGE

        self.cdrom_type = identify_cdrom(device_name)
        if (self.cdrom_type & CD_IMAGE):
            self.cdda = CDImage(device_name, self.cdrom_type)
        else:
            self.cdda = CDDA(device_name)
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
            #apply sample offset only to physical CD drives
            from audiotools.cdio import CD_IMAGE

            if (self.cdrom_type & CD_IMAGE):
                sample_offset = 0
            else:
                try:
                    sample_offset = int(config.get_default("System",
                                                           "cdrom_read_offset",
                                                           "0"))
                except ValueError:
                    sample_offset = 0

            reader = CDTrackReader(self.cdda,
                                   int(key),
                                   self.perform_logging)
            start_sector = reader.start
            end_sector = reader.end

            #apply sample offset, if any
            if (sample_offset > 0):
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

            # #if logging, wrap reader in AccurateRip checksummer
            # if (self.perform_logging):
            #     reader = CDTrackReaderAccurateRipCRC(
            #         reader,
            #         int(key),
            #         self.total_tracks,
            #         end_sector - start_sector + 1)

            return reader

    def __iter__(self):
        for i in range(1, self.total_tracks + 1):
            yield self[i]

    def length(self):
        """returns the length of the CD in CD frames"""

        #lead-in should always be 150
        return self.last_sector() + 150 + 1

    def close(self):
        """closes the CDDA device"""

        pass

    def first_sector(self):
        """returns the first sector's location, in CD frames"""

        return self.cdda.first_sector()

    def last_sector(self):
        """returns the last sector's location, in CD frames"""

        return self.cdda.last_sector()

    def freedb_disc_id(self):
        from .freedb import DiscID

        return DiscID(offsets=[t.offset() for t in self],
                      total_length=self.last_sector(),
                      track_count=len(self))

    def musicbrainz_disc_id(self):
        from .musicbrainz import DiscID

        return DiscID(first_track_number=1,
                      last_track_number=len(self),
                      lead_out_offset=self.last_sector() + 150 + 1,
                      offsets=[t.offset() for t in self])

    def metadata_lookup(self, musicbrainz_server="musicbrainz.org",
                        musicbrainz_port=80,
                        freedb_server="us.freedb.org",
                        freedb_port=80,
                        use_musicbrainz=True,
                        use_freedb=True):
        """generates a set of MetaData objects from CD

        returns a metadata[c][t] list of lists
        where 'c' is a possible choice
        and 't' is the MetaData for a given track (starting from 0)

        this will always return at least one choice,
        which may be a list of largely empty MetaData objects
        if no match can be found for the CD
        """

        return metadata_lookup(first_track_number=1,
                               last_track_number=len(self),
                               offsets=[t.offset() for t in self],
                               lead_out_offset=self.last_sector() + 150 + 1,
                               total_length=self.last_sector(),
                               musicbrainz_server=musicbrainz_server,
                               musicbrainz_port=musicbrainz_port,
                               freedb_server=freedb_server,
                               freedb_port=freedb_port,
                               use_musicbrainz=use_musicbrainz,
                               use_freedb=use_freedb)


class PCMReaderWindow:
    """a class for cropping a PCMReader to a specific window of frames"""

    def __init__(self, pcmreader, initial_offset, pcm_frames):
        """initial_offset is how many frames to crop, and may be negative
        pcm_frames is the total length of the window

        if the window is outside the PCMReader's data
        (that is, initial_offset is negative, or
        pcm_frames is longer than the total stream)
        those samples are padded with 0s"""

        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample

        self.initial_offset = initial_offset
        self.pcm_frames = pcm_frames

    def read(self, pcm_frames):
        if (self.pcm_frames > 0):
            if (self.initial_offset == 0):
                #once the initial offset is accounted for,
                #read a framelist from the pcmreader

                framelist = self.pcmreader.read(pcm_frames)
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
                framelist = self.pcmreader.read(pcm_frames)
                while (self.initial_offset > framelist.frames):
                    self.initial_offset -= framelist.frames
                    framelist = self.pcmreader.read(pcm_frames)

                (removed, framelist) = framelist.split(self.initial_offset)
                self.initial_offset -= removed.frames
                if (framelist.frames > 0):
                    if (framelist.frames <= self.pcm_frames):
                        self.pcm_frames -= framelist.frames
                        return framelist
                    else:
                        (framelist, removed) = framelist.split(self.pcm_frames)
                        self.pcm_frames = 0
                        return framelist
                else:
                    #if the entire framelist is cropped,
                    #return another one entirely
                    return self.read(pcm_frames)
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
    """a container for CD reading log information, implemented as a dict"""

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
    """a PCMReader-compatible object which reads from CDDA"""

    def __init__(self, cdda, track_number, perform_logging=True):
        """cdda is a cdio.CDDA object.  track_number is offset from 1"""

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
        """returns this track's CD offset, in CD frames"""

        return self.start + 150

    def length(self):
        """returns this track's length, in CD frames"""

        return self.end - self.start + 1

    def log(self, i, v):
        """adds a log entry to the track's rip_log

        this is meant to be called from CD reading callbacks"""

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
            s = self.cdda.read_sectors(min(sectors,
                                           self.end - self.position + 1))
            self.position += sectors
            return s
        else:
            return pcm.from_list([], 2, 16, True)

    def read(self, pcm_frames):
        """try to read a pcm.FrameList with the given number of PCM frames

        for CD reading, this will be a sector-aligned number"""

        #returns a sector-aligned number of PCM frames
        #(divisible by 588 frames, basically)
        #or at least 1 sector's worth, if "pcm_frames" is too small
        return self.__read_sectors__(max(pcm_frames / 588, 1))

    def close(self):
        """closes the CD track for reading"""

        self.position = self.start
        self.cursor_placed = False


class CDTrackReaderAccurateRipCRC:
    def __init__(self, cdtrackreader,
                 track_number, track_total,
                 total_sectors):
        self.cdtrackreader = cdtrackreader
        self.accuraterip_crc = AccurateRipTrackCRC()
        if (track_number == 1):
            self.prefix_0s = 5 * (44100 / 75) - 1
        else:
            self.prefix_0s = 0
        if (track_number == track_total):
            postfix_0s = 5 * (44100 / 75)
        else:
            postfix_0s = 0

        self.checksum_window = ((total_sectors * (44100 / 75)) -
                                (self.prefix_0s + postfix_0s))

        self.sample_rate = 44100
        self.channels = 2
        self.channel_mask = 0x3
        self.bits_per_sample = 16

        self.cdda = cdtrackreader.cdda
        self.track_number = track_number
        self.rip_log = cdtrackreader.rip_log

    def offset(self):
        return self.cdtrackreader.offset()

    def length(self):
        return self.cdtrackreader.length()

    def log(self):
        return self.cdtrackreader.log()

    def read(self, pcm_frames):
        frame = self.cdtrackreader.read(pcm_frames)
        crc_frame = frame

        if (self.prefix_0s > 0):
            #substitute frame samples for prefix 0s
            (substitute, remainder) = crc_frame.split(self.prefix_0s)
            self.accuraterip_crc.update(pcm.from_list(
                    [0] * len(substitute), 2, 16, True))
            self.prefix_0s -= substitute.frames
            crc_frame = remainder

        if (crc_frame.frames > self.checksum_window):
            #ensure PCM frames outside the window are substituted also
            (remainder, substitute) = crc_frame.split(self.checksum_window)
            self.checksum_window -= remainder.frames
            self.accuraterip_crc.update(remainder)
            self.accuraterip_crc.update(pcm.from_list(
                    [0] * len(substitute), 2, 16, True))
        else:
            self.checksum_window -= crc_frame.frames
            self.accuraterip_crc.update(crc_frame)

        #no matter how the CRC is updated,
        #return the original FrameList object as-is
        return frame

    def close(self):
        self.cdtrackreader.close()


#returns the value in item_list which occurs most often
def most_numerous(item_list, empty_list="", all_differ=""):
    """returns the value in the item list which occurs most often
    if list has no items, returns 'empty_list'
    if all items differ, returns 'all_differ'"""

    counts = {}

    if (len(item_list) == 0):
        return empty_list

    for item in item_list:
        counts.setdefault(item, []).append(item)

    (item,
     max_count) = sorted([(item, len(counts[item])) for item in counts.keys()],
                         lambda x, y: cmp(x[1], y[1]))[-1]
    if ((max_count < len(item_list)) and (max_count == 1)):
        return all_differ
    else:
        return item

__most_numerous__ = most_numerous


#######################
#CD MetaData Lookup
#######################


def metadata_lookup(first_track_number, last_track_number,
                    offsets, lead_out_offset, total_length,
                    musicbrainz_server="musicbrainz.org",
                    musicbrainz_port=80,
                    freedb_server="us.freedb.org",
                    freedb_port=80,
                    use_musicbrainz=True,
                    use_freedb=True):
    """generates a set of MetaData objects from CD

    first_track_number and last_track_number are positive ints
    offsets is a list of track offsets, in CD frames
    lead_out_offset is the offset of the "lead-out" track, in CD frames
    total_length is the total length of the disc, in CD frames

    returns a metadata[c][t] list of lists
    where 'c' is a possible choice
    and 't' is the MetaData for a given track (starting from 0)

    this will always return at least one choice,
    which may be a list of largely empty MetaData objects
    if no match can be found for the CD
    """

    assert(last_track_number >= first_track_number)
    track_count = (last_track_number + 1) - first_track_number
    assert(track_count == len(offsets))

    matches = []

    #MusicBrainz takes precedence over FreeDB
    if (use_musicbrainz):
        from . import musicbrainz
        from urllib2 import HTTPError
        from xml.parsers.expat import ExpatError
        try:
            matches.extend(musicbrainz.perform_lookup(
                    first_track_number=first_track_number,
                    last_track_number=last_track_number,
                    lead_out_offset=lead_out_offset,
                    offsets=offsets,
                    musicbrainz_server=musicbrainz_server,
                    musicbrainz_port=musicbrainz_port))
        except (HTTPError, ExpatError):
            pass

    if (use_freedb):
        from . import freedb
        from urllib2 import HTTPError
        try:
            matches.extend(freedb.perform_lookup(
                    offsets=offsets,
                    total_length=total_length,
                    track_count=track_count,
                    freedb_server=freedb_server,
                    freedb_port=freedb_port))
        except (HTTPError, ValueError), err:
            pass

    if (len(matches) == 0):
        #no matches, so build a set of dummy metadata
        return [[MetaData(track_number=i,
                          track_total=track_count)
                 for i in xrange(first_track_number, last_track_number + 1)]]
    else:
        return matches


def track_metadata_lookup(audiofiles,
                          musicbrainz_server="musicbrainz.org",
                          musicbrainz_port=80,
                          freedb_server="us.freedb.org",
                          freedb_port=80,
                          use_musicbrainz=True,
                          use_freedb=True):
    """given a list of AudioFile objects,
    this treats them as a single CD
    and generates a set of MetaData objects pulled from lookup services

    returns a metadata[c][t] list of lists
    where 'c' is a possible choice
    and 't' is the MetaData for a given track (starting from 0)

    this will always return at least one choice,
    which may be a list of largely empty MetaData objects
    if no match can be found for the CD
    """

    audiofiles.sort(lambda x,y: cmp(x.track_number(), y.track_number()))
    track_frames = [f.cd_frames() for f in audiofiles]
    track_numbers = [f.track_number() for f in audiofiles]

    return metadata_lookup(
        first_track_number=(min(track_numbers)
                            if None not in track_numbers else 1),
        last_track_number=(max(track_numbers)
                           if None not in track_numbers else
                           len(track_numbers)),
        offsets=[150 + sum(track_frames[0:i]) for i in
                 xrange(len(track_frames))],
        lead_out_offset=150 + sum(track_frames),
        total_length=sum(track_frames) - 1,
        musicbrainz_server=musicbrainz_server,
        musicbrainz_port=musicbrainz_port,
        freedb_server=freedb_server,
        freedb_port=freedb_port,
        use_musicbrainz=use_musicbrainz,
        use_freedb=use_freedb)


#######################
#DVD-Audio Discs
#######################


from .dvda import DVDAudio
from .dvda import InvalidDVDA


#######################
#Multiple Jobs Handling
#######################


class ExecQueue:
    """a class for running multiple jobs in parallel"""

    def __init__(self):
        self.todo = []
        self.return_values = set([])

    def execute(self, function, args, kwargs=None):
        """queues the given function with argument list and kwargs dict"""

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
        """performs the queued functions in separate subprocesses

        this runs "max_processes" number of functions at a time
        it works by spawning a new child process for each function,
        executing it and spawning a new child as each one exits
        therefore, any side effects beyond altering files on
        disk do not propogate back to the parent"""

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
    """a class for running multiple jobs and accumulating results"""

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
        if (pid > 0):  # parent
            os.close(pipe_write)
            reader = os.fdopen(pipe_read, 'r')
            return (pid, reader)
        else:          # child
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

        if the child job exited properly, that reader will have
        the pickled contents of the completed Python function
        and it can be used to find the child's PID to be waited for
        via the process pool
        in addition, the returned values of finished child processes
        are added to our "return_values" attribute"""

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

        yields the result of each executed function as they complete"""

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


class ProgressJobQueueComplete(Exception):
    pass


def output_progress(u, current, total):
    """given a unicode string and current/total integers,
    returns a u'[<current>/<total>]  <string>  unicode string
    indicating the current progress"""

    if (total > 1):
        return u"[%%%d.d/%%d]  %%s" % (len(str(total))) % (current, total, u)
    else:
        return u


class ExecProgressQueue:
    """a class for running multiple jobs in parallel with progress updates"""

    def __init__(self, progress_display):
        """takes a ProgressDisplay object"""

        self.progress_display = progress_display
        self.queued_jobs = []
        self.max_job_id = 0
        self.running_job_pool = {}
        self.results = {}
        self.exception = None
        self.completed_job_number = 0

    def execute(self, function,
                progress_text=None,
                completion_output=None,
                *args, **kwargs):
        """queues the given function and arguments to be run in parallel

        progress_text should be a unicode string to be displayed while running

        completion_output is either a unicode string,
        or a function which takes the result of the queued function
        and returns a unicode string for display
        once the queued function is complete
        """

        self.queued_jobs.append((self.max_job_id,
                                 progress_text,
                                 completion_output,
                                 function,
                                 args,
                                 kwargs))
        self.max_job_id += 1

    def execute_next_job(self):
        """executes the next queued job"""

        #pull job off queue
        (job_id,
         progress_text,
         completion_output,
         function,
         args,
         kwargs) = self.queued_jobs.pop(0)

        #add job to progress display
        if (progress_text is not None):
            self.progress_display.add_row(job_id, progress_text)
            self.progress_display.update_row(job_id, 0, 1)

        #spawn subprocess and add it to pool
        self.running_job_pool[job_id] = \
            __ProgressQueueJob__.spawn(function,
                                       args,
                                       kwargs,
                                       completion_output)

    def remove_job(self, job_id, job):
        """job_id is taken from the job_pool dict
        job is a __ProgressQueueJob__ object"""

        #add job's results to results dict
        (success, value) = job.result
        if (success):
            self.results[job_id] = value

            #remove job from pool
            del(self.running_job_pool[job_id])

            #remove job from progress display
            self.progress_display.delete_row(job_id)

            #increment finished job number for X/Y display
            self.completed_job_number += 1

            #display job's output message
            completion_output = job.completion_output
            if (completion_output is not None):
                if (callable(completion_output)):
                    output = completion_output(value)
                    if (output is not None):
                        self.progress_display.messenger.info(
                            output_progress(unicode(output),
                                            self.completed_job_number,
                                            self.max_job_id))
                else:
                    self.progress_display.messenger.info(
                        output_progress(unicode(completion_output),
                                        self.completed_job_number,
                                        self.max_job_id))
        else:
            #job raised an exception
            if (self.exception is None):
                #remove all other jobs from queue and set exception
                #as long as another job hasn't already
                self.queued_jobs = []
                self.exception = value

            #remove job from pool
            del(self.running_job_pool[job_id])

            #remove job from progress display
            self.progress_display.delete_row(job_id)

    def run(self, max_processes=1):
        """runs all the queued jobs in parallel"""

        if (len(self.queued_jobs) == 0):
            return

        import time

        #populate job pool with up to "max_processes" number of jobs
        for i in xrange(min(max_processes, len(self.queued_jobs))):
            self.execute_next_job()

        #while the pool still contains running jobs
        while (len(self.running_job_pool) > 0):
            #clear out old display
            self.progress_display.clear()

            #poll job pool for completed jobs
            for (job_id, job) in self.running_job_pool.items():
                if (job.is_completed()):
                    #display any output message
                    self.remove_job(job_id, job)

                    #and add new jobs from the queue as necessary
                    if (len(self.queued_jobs) > 0):
                        self.execute_next_job()
                else:
                    #update job's progress row with current progress
                    (current, total) = job.progress()
                    self.progress_display.update_row(job_id, current, total)

            #display new set of progress rows
            self.progress_display.refresh()

            #wait some amount of time before polling job pool again
            time.sleep(0.25)

        self.max_job_id = 0
        self.completed_job_number = 0

        if (self.exception is not None):
            raise self.exception


class __ProgressQueueJob__:
    def __init__(self, pid, progress, result, completion_output):
        """pid is the child process's PID
        progress is anonymous memory-mapped data of the child's progress
        result is a file object pipe for receiving the child's final result
        completion_output is a unicode string or function
        to execute upon the job's completion"""

        self.__pid__ = pid
        self.__progress__ = progress
        self.__result__ = result

        self.completion_output = completion_output

        # (True, value) indicates function succeeded and returned "value"
        # (False, exc) indicates function raised exception "exc"
        # None indicates the function hasn't yet completed
        self.result = None

    @classmethod
    def spawn(cls, function, args, kwargs, completion_output):
        """given an callable function args tuple and kwargs dict
        forks a child process with several pipes for polling progress
        and returns a __ProgressQueueJob__ object
        which can be polled for progress, waited for, or
        have return values extracted from"""

        import mmap
        import struct
        import cPickle

        progress = mmap.mmap(-1, 16)  # 2, 64-bit fields of progress data
        (r3, w3) = os.pipe()  # for sending final result from child->parent
        pid = os.fork()
        if (pid > 0):
            #parent
            os.close(w3)
            child_result = os.fdopen(r3, "rb")

            return cls(pid, progress, child_result, completion_output)
        else:
            #child
            os.close(r3)

            try:
                result = (True, function(*args,
                                         progress=
                                         __PollingProgress__(progress).progress,
                                         **kwargs))
            except Exception, exception:
                result = (False, exception)

            result_pipe = os.fdopen(w3, "wb")
            cPickle.dump(result, result_pipe)
            result_pipe.flush()
            result_pipe.close()
            progress.close()
            sys.exit(0)

    def is_completed(self):
        """returns True if the job is completed
        in that instance, self.result will be populated
        with the function's return value
        and the child process will be disposed of"""

        import cPickle

        if (os.waitpid(self.__pid__, os.WNOHANG) != (0, 0)):
            try:
                self.result = cPickle.load(self.__result__)
            except EOFError:
                #child died without returning a value
                #or raising any exception
                #which is unusual
                self.result = (True, None)
            self.__progress__.close()
            return True
        else:
            return False

    def progress(self):
        """polls child process for job's current progress
        and returns a (progress, total) pair of integers"""

        import struct

        self.__progress__.seek(0, 0)
        (current, total) = struct.unpack(">QQ", self.__progress__.read(16))

        return (current, total)


class __PollingProgress__:
    def __init__(self, memory):
        self.memory = memory

    def progress(self, current, total):
        import struct

        self.memory.seek(0, 0)
        self.memory.write(struct.pack(">QQ", current, total))

from .au import AuAudio
from .wav import WaveAudio
from .aiff import AiffAudio
from .flac import FlacAudio
from .flac import OggFlacAudio
from .wavpack import WavPackAudio
from .shn import ShortenAudio
from .mp3 import MP3Audio
from .mp3 import MP2Audio
from .vorbis import VorbisAudio
from .m4a import M4AAudio
from .m4a import ALACAudio
from .opus import OpusAudio

from .ape import ApeTag
from .flac import FlacMetaData
from .id3 import ID3CommentPair
from .id3v1 import ID3v1Comment
from .id3 import ID3v22Comment
from .id3 import ID3v23Comment
from .id3 import ID3v24Comment
from .m4a_atoms import M4A_META_Atom
from .vorbiscomment import VorbisComment
from .opus import OpusTags

AVAILABLE_TYPES = (FlacAudio,
                   OggFlacAudio,
                   MP3Audio,
                   MP2Audio,
                   WaveAudio,
                   VorbisAudio,
                   AiffAudio,
                   AuAudio,
                   M4AAudio,
                   ALACAudio,
                   WavPackAudio,
                   ShortenAudio,
                   OpusAudio)

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
