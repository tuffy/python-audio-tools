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


from audiotools import VERSION,Con,cStringIO,sys,re,MetaData,AlbumMetaData,__most_numerous__,DummyAudioFile

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
            offset += track.cd_frames()
        disc_length = offset / 75

        print >>xmcd,"#"
        print >>xmcd,"# Disc length: %d seconds" % (disc_length)
        print >>xmcd,"#"
        build_key_pair(xmcd,"DISCID",str(DiscID([f.cd_frames() for f in
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
        else:
            build_key_pair(xmcd,"TTITLE%d" % (i),u"")

    build_key_pair(xmcd,"EXTDD",u"")
    for (i,track) in enumerate(audiofiles):
        build_key_pair(xmcd,"EXTT%d" % (i),u"")

    build_key_pair(xmcd,"PLAYORDER",u"")

    return xmcd.getvalue()



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
