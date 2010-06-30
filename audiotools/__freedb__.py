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


from audiotools import (VERSION, Con, cStringIO, sys, re, MetaData,
                        AlbumMetaData, __most_numerous__,
                        DummyAudioFile, MetaDataFileException)

import gettext

gettext.install("audiotools", unicode=True)

#######################
#XMCD
#######################


class XMCDException(MetaDataFileException):
    """Raised if some error occurs parsing an XMCD file."""

    def __unicode__(self):
        return _(u"Invalid XMCD file")


class XMCD:
    """An XMCD file representation."""

    LINE_LIMIT = 78

        def __init__(self, values, offsets, length):
        """Fields are as follows:

        values  - a dict of key->value pairs such as "TTITLE0":u"Track Name"
        offsets - a list of track offset integers (in CD frames)
        length  - a total album length integer (in seconds)
        """

        self.__values__ = values
        self.offsets = offsets
        self.length = length

    def __repr__(self):
        return "XMCD(%s,%s,%s)" % (repr(self.__values__),
                                   repr(self.offsets),
                                   repr(self.length))

    def __getitem__(self, key):
        return self.__values__[key]

    def get(self, key, default):
        return self.__values__.get(key, default)

    def __setitem__(self, key, value):
        self.__values__[key] = value

    def __len__(self):
        return len(self.__values__)

    def keys(self):
        return self.__values__.keys()

    def values(self):
        return self.__values__.values()

    def items(self):
        return self.__values__.items()

    @classmethod
    def key_digits(cls, key):
        """Given a key, returns its digits as integer.

        For example:
        >>> key_digits('TTITLE0')
        0
        """

        import re

        d = re.search(r'\d+', key)
        if (d is not None):
            return int(d.group(0))
        else:
            return -1

    def build(self):
        """Returns the entire XMCD file as a string."""

        import string

        key_order = ['DISCID', 'DTITLE', 'DYEAR', 'TTITLE', 'EXTDD', 'EXTT',
                     'PLAYORDER']

        def by_pair(p1, p2):
            if (p1[0].rstrip(string.digits) in key_order):
                p1 = (key_order.index(p1[0].rstrip(string.digits)),
                      self.key_digits(p1[0]),
                      p1[0])
            else:
                p1 = (len(key_order),
                      self.key_digits(p1[0]),
                      p1[0])

            if (p2[0].rstrip(string.digits) in key_order):
                p2 = (key_order.index(p2[0].rstrip(string.digits)),
                      self.key_digits(p2[0]),
                      p2[0])
            else:
                p2 = (len(key_order),
                      self.key_digits(p2[0]),
                      p2[0])

            return cmp(p1, p2)

        def encode(u):
            return u.encode('utf-8')

        def split_fields(pairs):
            #returns index i which is less than l bytes from unicode string u
            def max_chars(u, l):
                for i in xrange(len(u.encode('utf-8')) + 1):
                    if (len(u[0:i].encode('utf-8')) > l):
                        return i - 1
                else:
                    return i

            for (key, value) in pairs:
                #line = u"%s=%s" % (key.decode('ascii'),value)
                keylen = len(key) + len("=")
                while ((keylen + len(value.encode('utf-8'))) >
                       XMCD.LINE_LIMIT):
                    #latin-1 lines might be shorter, but shouldn't be longer
                    #UTF-8 assumes the worst case
                    cut = max_chars(value, XMCD.LINE_LIMIT - len(key) -
                                    len('='))
                    partial = value[0:cut]
                    value = value[cut:]
                    yield u"%s=%s" % (key.decode('ascii'), partial)

                yield u"%s=%s" % (key.decode('ascii'), value)

        return encode((u"# xmcd\n#\n# Track frame offsets:\n" +
                       u"%(offsets)s\n#\n# Disc length: %(length)s " +
                       u"seconds\n#\n%(fields)s\n") % \
            {"offsets": u"\n".join(["#\t%s" % (offset)
                                   for offset in self.offsets]),
             "length": self.length,
             "fields": "\n".join(split_fields(sorted(self.items(), by_pair)))})

    @classmethod
    def read(cls, filename):
        """Given a filename, returns an XMCD object if possible.

        May raise XMCDException if the file cannot be read or parsed."""

        import StringIO
        import re

        try:
            f = open(filename, 'r')
        except IOError:
            raise XMCDException(filename)

        try:
            data = f.read()
            try:
                data = data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    data = data.decode('ISO-8859-1')
                except UnicodeDecodeError:
                    raise XMCDException(filename)
        finally:
            f.close()

        return cls.read_data(data)

    @classmethod
    def read_data(cls, data):
        """Returns an XMCD object from a unicode string of XMCD data."""

        if (not data.startswith(u"# xmcd")):
            raise XMCDException("")

        disc_length = re.search(r'# Disc length: (\d+)', data)
        if (disc_length is not None):
            disc_length = int(disc_length.group(1))

        track_lengths = re.compile(r'# Track frame offsets:\s+[#\s\d]+',
                                   re.DOTALL).search(data)
        if (track_lengths is not None):
            track_lengths = map(int,
                                re.findall(r'\d+', track_lengths.group(0)))

        fields = {}

        for line in re.findall(r'.+=.*[\r\n]', data):
            (field, value) = line.split(u'=', 1)
            field = field.encode('ascii')
            value = value.rstrip('\r\n')
            if (field in fields.keys()):
                fields[field] += value
            else:
                fields[field] = value

        return XMCD(values=fields, offsets=track_lengths, length=disc_length)

    @classmethod
    def from_files(cls, audiofiles):
        """Returns an XMCD object from a list of AudioFile objects.

        These objects are presumably from the same album.
        If not, these heuristics may generate something unexpected.
        """

        def track_string(track, album_artist, metadata):
            if (track.track_number() in metadata.keys()):
                metadata = metadata[track.track_number()]
                if (metadata.artist_name == album_artist):
                    return metadata.track_name
                else:
                    return u"%s / %s" % (metadata.artist_name,
                                         metadata.track_name)
            else:
                return u""

        audiofiles = [f for f in audiofiles if f.track_number() != 0]
        audiofiles.sort(lambda t1, t2: cmp(t1.track_number(),
                                           t2.track_number()))

        discid = DiscID([track.cd_frames() for track in audiofiles])

        metadata = dict([(t.track_number(), t.get_metadata())
                          for t in audiofiles
                         if (t.get_metadata() is not None)])

        artist_names = [m.artist_name for m in metadata.values()]
        if (len(artist_names) == 0):
            album_artist = u""
        elif ((len(artist_names) > 1) and
              (len(set(artist_names)) == len(artist_names))):
            #if all track artists are different, don't pick one
            album_artist = u"Various"
        else:
            album_artist = __most_numerous__(artist_names)

        return XMCD(dict([("DISCID", str(discid).decode('ascii')),
                          ("DTITLE", u"%s / %s" % \
                               (album_artist,
                                __most_numerous__([m.album_name for m in
                                                   metadata.values()]))),
                          ("DYEAR", __most_numerous__([m.year for m in
                                                      metadata.values()])),
                          ("EXTDD", u""),
                          ("PLAYORDER", u"")] + \
                         [("TTITLE%d" % (track.track_number() - 1),
                           track_string(track, album_artist, metadata))
                          for track in audiofiles] + \
                         [("EXTT%d" % (track.track_number() - 1),
                           u"")
                           for track in audiofiles]),
                    discid.offsets(),
                    (discid.length() / 75) + 2)

    @classmethod
    def from_cuesheet(cls, cuesheet, total_frames, sample_rate, metadata=None):
        """Generates an XMCD object from a cuesheet.

        This must also include a total_frames and sample_rate integer.
        This works by generating a set of empty tracks and calling
        the from_tracks() method to build an XMCD file with
        the proper placeholders.
        metadata, if present, is applied to all tracks.
        """

        if (metadata is None):
            metadata = MetaData()

        return cls.from_files([DummyAudioFile(
                    length=(pcm_frames * 75) / sample_rate,
                    metadata=metadata,
                    track_number=i + 1) for (i, pcm_frames) in enumerate(
                    cuesheet.pcm_lengths(total_frames))])

    def metadata(self):
        """Returns an AlbumMetaData object."""

        dtitle = self.get('DTITLE', u'')
        if (u' / ' in dtitle):
            (album_artist, album_name) = dtitle.split(u' / ', 1)
        else:
            (album_artist, album_name) = (dtitle, dtitle)

        dyear = self.get('DYEAR', u'')

        tracks = []

        for key in self.keys():
            if (key.startswith('TTITLE')):
                tracknum = self.key_digits(key)
                if (tracknum == -1):
                    continue

                ttitle = self[key]

                if (u' / ' in ttitle):
                    (track_artist, track_name) = ttitle.split(u' / ', 1)
                else:
                    track_name = ttitle
                    track_artist = album_artist

                tracks.append(MetaData(track_name=track_name,
                                       track_number=tracknum + 1,
                                       album_name=album_name,
                                       artist_name=track_artist,
                                       year=dyear))

        track_total = max([t.track_number for t in tracks])
        for t in tracks:
            t.track_total = track_total
        tracks.sort(lambda t1, t2: cmp(t1.track_number, t2.track_number))
        return AlbumMetaData(tracks)


#######################
#FREEDB
#######################

class DiscID:
    """An object representing a 32 bit FreeDB disc ID value."""

    DISCID = Con.Struct('discid',
                        Con.UBInt8('digit_sum'),
                        Con.UBInt16('length'),
                        Con.UBInt8('track_count'))


    def __init__(self, tracks=[], offsets=None, length=None, lead_in=150):
        """Fields are as follows:

        tracks  - a list of track lengths in CD frames
        offsets - a list of track offsets in CD frames
        length  - the length of the entire disc in CD frames
        lead_in - the location of the first track on the CD, in frames

        These fields are all optional.
        One will presumably fill them with data later in that event.
        """

        self.tracks = tracks
        self.__offsets__ = offsets
        self.__length__ = length
        self.__lead_in__ = lead_in

    @classmethod
    def from_cdda(cls, cdda):
        """Given a CDDA object, returns a populated DiscID."""

        tracks = list(cdda)

        return cls(tracks=[t.length() for t in tracks],
                   offsets=[t.offset() for t in tracks],
                   length=cdda.length(),
                   lead_in=tracks[0].offset())

    def add(self, track):
        """Adds a new track length, in CD frames."""

        self.tracks.append(track)

    def offsets(self):
        """Returns a list of calculated offset integers, from track lengths."""

        if (self.__offsets__ is None):
            offsets = [self.__lead_in__]

            for track in self.tracks[0:-1]:
                offsets.append(track + offsets[-1])

            return offsets
        else:
            return self.__offsets__

    def length(self):
        """Returns the total length of the disc, in seconds."""

        if (self.__length__ is None):
            return sum(self.tracks)
        else:
            return self.__length__

    def idsuffix(self):
        """Returns a FreeDB disc ID suffix string.

        This is for making server queries."""

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
        """Returns the entire FreeDB disc ID, including suffix."""

        return str(self) + " " + self.idsuffix()

    def toxmcd(self, output):
        """Writes a newly created XMCD file to output.

        Its values are populated from this DiscID's fields."""

        output.write(XMCD.from_files(
            [DummyAudioFile(length, None, i + 1)
             for (i, length) in enumerate(self.tracks)]).build())


class FreeDBException(Exception):
    """Raised if some problem occurs during FreeDB querying."""

    pass


class FreeDB:
    """A class for performing queries on a FreeDB or compatible server.

    This operates using the original FreeDB client-server protocol."""

    LINE = re.compile(r'\d\d\d\s.+')

    def __init__(self, server, port, messenger):
        """server is a string, port is an int, messenger is a Messenger.

        Queries are sent to the server, and output to the messenger."""

        self.server = server
        self.port = port
        self.socket = None
        self.r = None
        self.w = None
        self.messenger = messenger

    def connect(self):
        """Performs the initial connection."""

        import socket

        try:
            self.messenger.info(_(u"Connecting to \"%s\"") % (self.server))

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server, self.port))

            self.r = self.socket.makefile("rb")
            self.w = self.socket.makefile("wb")

            (code, msg) = self.read()  # the welcome message
            if (code == 201):
                self.messenger.info(_(u"Connected ... attempting to login"))
            else:
                self.r.close()
                self.w.close()
                self.socket.close()
                raise FreeDBException(_(u"Invalid hello message"))

            self.write("cddb hello user %s %s %s" % \
                       (socket.getfqdn(), "audiotools", VERSION))

            (code, msg) = self.read()  # the handshake successful message
            if (code != 200):
                self.r.close()
                self.w.close()
                self.socket.close()
                raise FreeDBException(_(u"Handshake unsuccessful"))

            self.write("proto 6")

            (code, msg) = self.read()  # the protocol successful message
            if ((code != 200) and (code != 201)):
                self.r.close()
                self.w.close()
                self.socket.close()
                raise FreeDBException(_(u"Protocol change unsuccessful"))

        except socket.error, err:
            raise FreeDBException(err[1])

    def close(self):
        """Closes an open connection."""

        self.messenger.info(_(u"Closing connection"))

        self.write("quit")
        (code, msg) = self.read()  # the quit successful message

        self.r.close()
        self.w.close()
        self.socket.close()

    def write(self, line):
        """Writes a single command line to the server."""

        if (self.socket is not None):
            self.w.write(line)
            self.w.write("\r\n")
            self.w.flush()

    def read(self):
        """Reads a result line from the server."""

        line = self.r.readline()
        if (FreeDB.LINE.match(line)):
            return (int(line[0:3]), line[4:].rstrip("\r\n"))
        else:
            return (None, line.rstrip("\r\n"))

    def query(self, disc_id):
        """Given a DiscID, performs an album query and returns matches.

        Each match is a (category, id) pair, which the user may
        need to decide between."""

        matches = []

        self.messenger.info(
            _(u"Sending Disc ID \"%(disc_id)s\" to server \"%(server)s\"") % \
                {"disc_id": str(disc_id).decode('ascii'),
                 "server": self.server.decode('ascii', 'replace')})

        self.write("cddb query " + disc_id.freedb_id())
        (code, msg) = self.read()
        if (code == 200):
            matches.append(msg)
        elif ((code == 211) or (code == 210)):
            while (msg != "."):
                (code, msg) = self.read()
                if (msg != "."):
                    matches.append(msg)

        if (len(matches) == 1):
            self.messenger.info(_(u"1 match found"))
        else:
            self.messenger.info(_(u"%s matches found") % (len(matches)))

        return map(lambda m: m.split(" ", 2), matches)

    def read_data(self, category, id, output):
        """Reads the FreeDB entry matching category and id to output.

        category and id are raw strings, as returned by query().
        output is an open file object.
        """

        self.write("cddb read " + category + " " + id)
        (code, msg) = self.read()
        if (code == 210):
            line = self.r.readline()
            while (line.strip() != "."):
                output.write(line)
                line = self.r.readline()
        else:
            print >> sys.stderr, (code, msg)


class FreeDBWeb(FreeDB):
    """A class for performing queries on a FreeDB or compatible server.

    This operates using the FreeDB web-based protocol."""

    def __init__(self, server, port, messenger):
        """server is a string, port is an int, messenger is a Messenger.

        Queries are sent to the server, and output to the messenger."""

        self.server = server
        self.port = port
        self.connection = None
        self.messenger = messenger

    def connect(self):
        """Performs the initial connection."""

        import httplib

        self.connection = httplib.HTTPConnection(self.server, self.port)

    def close(self):
        """Closes an open connection."""

        if (self.connection is not None):
            self.connection.close()

    def write(self, line):
        """Writes a single command line to the server."""

        import urllib
        import socket

        u = urllib.urlencode({"hello": "user %s %s %s" % \
                                      (socket.getfqdn(),
                                       "audiotools",
                                       VERSION),
                              "proto": str(6),
                              "cmd": line})

        try:
            self.connection.request(
                "POST",
                "/~cddb/cddb.cgi",
                u,
                {"Content-type": "application/x-www-form-urlencoded",
                 "Accept":  "text/plain"})
        except socket.error, msg:
            raise FreeDBException(str(msg))

    def read(self):
        """Reads a result line from the server."""

        response = self.connection.getresponse()
        return response.read()

    def __parse_line__(self, line):
        if (FreeDB.LINE.match(line)):
            return (int(line[0:3]), line[4:].rstrip("\r\n"))
        else:
            return (None, line.rstrip("\r\n"))

    def query(self, disc_id):
        """Given a DiscID, performs an album query and returns matches.

        Each match is a (category, id) pair, which the user may
        need to decide between."""

        matches = []

        self.messenger.info(
            _(u"Sending Disc ID \"%(disc_id)s\" to server \"%(server)s\"") % \
                {"disc_id": str(disc_id).decode('ascii'),
                 "server": self.server.decode('ascii', 'replace')})

        self.write("cddb query " + disc_id.freedb_id())
        data = cStringIO.StringIO(self.read())
        (code, msg) = self.__parse_line__(data.readline())
        if (code == 200):
            matches.append(msg)
        elif ((code == 211) or (code == 210)):
            while (msg != "."):
                (code, msg) = self.__parse_line__(data.readline())
                if (msg != "."):
                    matches.append(msg)

        if (len(matches) == 1):
            self.messenger.info(_(u"1 match found"))
        else:
            self.messenger.info(_(u"%s matches found") % (len(matches)))

        return map(lambda m: m.split(" ", 2), matches)

    def read_data(self, category, id, output):
        """Reads the FreeDB entry matching category and id to output.

        category and id are raw strings, as returned by query().
        output is an open file object.
        """

        self.write("cddb read " + category + " " + id)
        data = cStringIO.StringIO(self.read())
        (code, msg) = self.__parse_line__(data.readline())
        if (code == 210):
            line = data.readline()
            while (line.strip() != "."):
                output.write(line)
                line = data.readline()
        else:
            print >> sys.stderr, (code, msg)


#matches is a list of (category,disc_id,title) tuples returned from
#FreeDB.query().  If the length of that list is 1, return the first
#item.  If the length is greater than one, present the user a list of
#choices and force him/her to pick the closest match for the CD.
#That data can then be sent to FreeDB.read_data()
def __select_match__(matches, messenger):
    if (len(matches) == 1):
        return matches[0]
    elif (len(matches) < 1):
        return None
    else:
        messenger.info(_(u"Please Select the Closest Match:"))
        selected = 0
        while ((selected < 1) or (selected > len(matches))):
            for i in range(len(matches)):
                messenger.info(_(u"%(choice)s) [%(genre)s] %(name)s") % \
                                   {"choice": i + 1,
                                    "genre": matches[i][0],
                                    "name": matches[i][2].decode('utf-8',
                                                                 'replace')})
            try:
                messenger.partial_info(_(u"Your Selection [1-%s]:") % \
                                           (len(matches)))
                selected = int(sys.stdin.readline().strip())
            except ValueError:
                selected = 0

        return matches[selected - 1]


def __select_default_match__(matches, selection):
    if (len(matches) < 1):
        return None
    else:
        try:
            return matches[selection]
        except IndexError:
            return matches[0]


def get_xmcd(disc_id, output, freedb_server, freedb_server_port,
             messenger, default_selection=None):
    """Runs through the entire FreeDB querying sequence.

    Fields are as follows:
    disc_id           - a DiscID object
    output            - an open file object for writing
    freedb_server     - a server name string
    freedb_port       - a server port int
    messenger         - a Messenger object
    default_selection - if given, the default match to choose
    """

    try:
        freedb = FreeDBWeb(freedb_server, freedb_server_port, messenger)
        freedb.connect()
    except FreeDBException, msg:
        #if an exception occurs during the opening,
        #freedb will auto-close its sockets
        raise IOError(str(msg))

    try:
        matches = freedb.query(disc_id)
        #HANDLE MULTIPLE MATCHES, or NO MATCHES
        if (len(matches) > 0):
            if (default_selection is None):
                (category, idstring, title) = __select_match__(
                    matches, messenger)
            else:
                (category, idstring, title) = __select_default_match__(
                    matches, default_selection)

            freedb.read_data(category, idstring, output)
            output.close()

        freedb.close()
    except FreeDBException, msg:
        #otherwise, close the sockets manually
        freedb.close()
        raise IOError(str(msg))

    if (len(matches) > 0):
        messenger.info(_(u"%s written") % (messenger.filename(output.name)))
    return len(matches)
