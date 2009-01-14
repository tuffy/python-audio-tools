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


from audiotools import VERSION,Con,cStringIO,sys,re,MetaData,AlbumMetaData,__most_numerous__,DummyAudioFile

#######################
#XMCD
#######################

class XMCDException(Exception): pass

class XMCD:
    LINE_LIMIT = 78

    #values is a dict of key->value pairs
    #such as "TTITLE0":u"Track Name"
    #offsets is a list of track offset integers (in CD frames)
    #length is a total album length integer (in seconds)
    def __init__(self,values,offsets,length):
        self.__values__ = values
        self.offsets = offsets
        self.length = length

    def __repr__(self):
        return "XMCD(%s,%s,%s)" % (repr(self.__values__),
                                   repr(self.offsets),
                                   repr(self.length))

    def __getitem__(self,key):
        return self.__values__[key]

    def get(self,key,default):
        return self.__values__.get(key,default)

    def __setitem__(self,key,value):
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
    def key_digits(cls,key):
        import re

        d = re.search(r'\d+',key)
        if (d is not None):
            return int(d.group(0))
        else:
            return -1

    def build(self):
        import string

        key_order = ['DISCID','DTITLE','DYEAR','TTITLE','EXTDD','EXTT',
                     'PLAYORDER']

        def by_pair(p1,p2):
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

            return cmp(p1,p2)

        def encode(u):
            try:
                return u.encode('ISO-8859-1')
            except UnicodeEncodeError:
                return u.encode('utf-8')

        def split_fields(pairs):
            #returns index i which is less than l bytes from unicode string u
            def max_chars(u,l):
                for i in xrange(len(u.encode('utf-8')) + 1):
                    if (len(u[0:i].encode('utf-8')) > l):
                        return i - 1
                else:
                    return i

            for (key,value) in pairs:
                #line = u"%s=%s" % (key.decode('ascii'),value)
                keylen = len(key) + len("=")
                while ((keylen + len(value.encode('utf-8'))) > XMCD.LINE_LIMIT):
                    #latin-1 lines might be shorter, but shouldn't be longer
                    #UTF-8 assumes the worst case
                    cut = max_chars(value,XMCD.LINE_LIMIT - len(key) - len('='))
                    partial = value[0:cut]
                    value = value[cut:]
                    yield u"%s=%s" % (key.decode('ascii'),partial)

                yield u"%s=%s" % (key.decode('ascii'),value)

        return encode(u"# xmcd\n#\n# Track frame offsets:\n%(offsets)s\n#\n# Disc length: %(length)s seconds\n#\n%(fields)s\n" % \
            {"offsets":u"\n".join(["#\t%s" % (offset)
                                   for offset in self.offsets]),
             "length":self.length,
             "fields":"\n".join(split_fields(sorted(self.items(),by_pair)))})

    @classmethod
    def read(cls, filename):
        import StringIO,re

        f = open(filename,'r')
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

    #takes a unicode string of XMCD data
    #returns an XMCD object
    @classmethod
    def read_data(cls,data):
        if (not data.startswith(u"# xmcd")):
            raise XMCDException("")

        disc_length = re.search(r'# Disc length: (\d+)',data)
        if (disc_length is not None):
            disc_length = int(disc_length.group(1))

        track_lengths = re.compile(r'# Track frame offsets:\s+[#\s\d]+',
                                   re.DOTALL).search(data)
        if (track_lengths is not None):
            track_lengths = map(int,re.findall(r'\d+',track_lengths.group(0)))

        fields = {}

        for line in re.findall(r'.+=.*[\r\n]',data):
            (field,value) = line.split(u'=',1)
            field = field.encode('ascii')
            value = value.rstrip('\r\n')
            if (field in fields.keys()):
                fields[field] += value
            else:
                fields[field] = value

        return XMCD(values=fields,offsets=track_lengths,length=disc_length)

    #audiofiles should be a list of AudioFile-compatible objects
    #from the same album, possibly with valid MetaData
    @classmethod
    def from_files(cls, audiofiles):
        def track_string(track,album_artist,metadata):
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
        audiofiles.sort(lambda t1,t2: cmp(t1.track_number(),
                                          t2.track_number()))

        discid = DiscID([track.cd_frames() for track in audiofiles])

        metadata = dict([(t.track_number(),t.get_metadata())
                          for t in audiofiles
                         if (t.get_metadata() is not None)])

        artist_names = [m.artist_name for m in metadata.values()]
        if (len(set(artist_names)) == len(artist_names)):
            #if all track artists are different, don't pick one
            album_artist = u"Various"
        else:
            album_artist = __most_numerous__(artist_names)

        return XMCD(dict([("DISCID",str(discid).decode('ascii')),
                          ("DTITLE",u"%s / %s" % \
                               (album_artist,
                                __most_numerous__([m.album_name for m in
                                                   metadata.values()]))),
                          ("DYEAR",__most_numerous__([m.year for m in
                                                      metadata.values()])),
                          ("EXTDD",u""),
                          ("PLAYORDER",u"")] + \
                         [("TTITLE%d" % (track.track_number() - 1),
                           track_string(track,album_artist,metadata))
                          for track in audiofiles] + \
                         [("EXTT%d" % (track.track_number() - 1),
                           u"")
                           for track in audiofiles]),
                    discid.offsets(),
                    (discid.length() / 75) + 2)

    def metadata(self):
        dtitle = self.get('DTITLE',u'')
        if (u' / ' in dtitle):
            (album_artist,album_name) = dtitle.split(u' / ',1)
        else:
            album_name = dtitle
            artist_name = u''

        dyear = self.get('DYEAR',u'')

        tracks = []

        for key in self.keys():
            if (key.startswith('TTITLE')):
                tracknum = self.key_digits(key)
                if (tracknum == -1):
                    continue

                ttitle = self[key]

                if (u' / ' in ttitle):
                    (track_artist,track_name) = ttitle.split(u' / ',1)
                else:
                    track_name = ttitle
                    track_artist = album_artist

                tracks.append(MetaData(track_name=track_name,
                                       track_number=tracknum + 1,
                                       album_name=album_name,
                                       artist_name=track_artist,
                                       year=dyear))

        tracks.sort(lambda t1,t2: cmp(t1.track_number,t2.track_number))
        return AlbumMetaData(tracks)


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
            offsets = [self.__lead_in__]

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
        output.write(XMCD.from_files(
            [DummyAudioFile(length,None,i + 1)
             for (i,length) in enumerate(self.tracks)]).build())

class FreeDBException(Exception): pass

class FreeDB:
    LINE = re.compile(r'\d\d\d\s.+')

    def __init__(self, server, port, display_output=True):
        self.server = server
        self.port = port
        self.socket = None
        self.r = None
        self.w = None
        self.display_output = display_output

    def connect(self):
        import socket

        try:
            if (self.display_output):
                print >>sys.stderr,"* Connecting to \"%s\"" % (self.server)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server,self.port))

            self.r = self.socket.makefile("rb")
            self.w = self.socket.makefile("wb")

            (code,msg) = self.read()  #the welcome message
            if (code == 201):
                if (self.display_output):
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
        if (self.display_output):
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

        if (self.display_output):
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

        if (self.display_output):
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
    def __init__(self, server, port, display_output=True):
        self.server = server
        self.port = port
        self.connection = None
        self.display_output = display_output

    def connect(self):
        import httplib

        self.connection = httplib.HTTPConnection(self.server,self.port)

    def close(self):
        if (self.connection != None):
            self.connection.close()

    def write(self, line):
        import urllib,socket

        u = urllib.urlencode({"hello":"user %s %s %s" % \
                                      (socket.getfqdn(),
                                       "audiotools",
                                       VERSION),
                              "proto":str(6),
                              "cmd":line})

        try:
            self.connection.request(
                "POST",
                "/~cddb/cddb.cgi",
                u,
                {"Content-type":"application/x-www-form-urlencoded",
                 "Accept": "text/plain"})
        except socket.error,msg:
            raise FreeDBException(str(msg))

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

        if (self.display_output):
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

        if (self.display_output):
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

def __select_default_match__(matches, selection):
    if (len(matches) < 1):
        return None
    else:
        try:
            return matches[selection]
        except IndexError:
            return matches[0]

#takes a DiscID value and a file handle for output
#and runs the entire FreeDB querying sequence
#the file handle is closed at the conclusion of this function
def get_xmcd(disc_id, output, freedb_server, freedb_server_port,
             default_selection=None, display_output=False):
    try:
        freedb = FreeDBWeb(freedb_server,freedb_server_port,display_output)
        freedb.connect()
    except FreeDBException,msg:
        #if an exception occurs during the opening,
        #freedb will auto-close its sockets
        output.close()
        raise IOError(str(msg))

    try:
        matches = freedb.query(disc_id)
        #HANDLE MULTIPLE MATCHES, or NO MATCHES
        if (len(matches) > 0):
            if (default_selection is None):
                (category,idstring,title) = __select_match__(matches)
            else:
                (category,idstring,title) = __select_default_match__(
                    matches,default_selection)

            freedb.read_data(category,idstring,output)
        else:
            disc_id.toxmcd(output)

        freedb.close()
    except FreeDBException,msg:
        #otherwise, close the sockets manually
        freedb.close()
        raise IOError(str(msg))

    output.close()
    if (display_output):
        print >>sys.stderr,"* %s written" % (output.name)
