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

from audiotools import MetaData,AlbumMetaData,MetaDataFileException
import urllib
import gettext

gettext.install("audiotools",unicode=True)

class MBDiscID:
    #tracks is a list of track lengths in CD frames
    #offsets, if present, is a list of track offsets in CD frames
    #length, if present, is the length of the entire disc in CD frames
    #lead_in is the location of the first track on the CD, in frames
    #first_track_number, last_track_number and lead_out_track_offset are ints
    def __init__(self, tracks=[], offsets=None, length=None, lead_in=150,
                 first_track_number = None, last_track_number = None,
                 lead_out_track_offset = None):
        self.tracks = tracks
        self.__offsets__ = offsets
        self.__length__ = length
        self.__lead_in__ = lead_in
        self.first_track_number = first_track_number
        self.last_track_number = last_track_number
        self.lead_out_track_offset = lead_out_track_offset

    def offsets(self):
        if (self.__offsets__ is None):
            offsets = [self.__lead_in__]

            for track in self.tracks[0:-1]:
                offsets.append(track + offsets[-1])

            return offsets
        else:
            return self.__offsets__

    #returns a MusicBrainz DiscID value as a string
    def __str__(self):
        from hashlib import sha1

        if (self.lead_out_track_offset is None):
            if (self.__length__ is None):
                lead_out_track_offset = sum(self.tracks) + self.__lead_in__
            else:
                lead_out_track_offset = self.__length__ + self.__lead_in__
        else:
            lead_out_track_offset = self.lead_out_track_offset

        if (self.first_track_number is None):
            first_track_number = 1
        else:
            first_track_number = self.first_track_number

        if (self.last_track_number is None):
            last_track_number = len(self.tracks)
        else:
            last_track_number = self.last_track_number

        digest = sha1("%02X%02X%s" % \
                      (first_track_number,
                       last_track_number,
                       "".join(["%08X" % (i) for i in
                                [lead_out_track_offset] +
                                self.offsets() +
                                ([0] * (99 - len(self.offsets())))])))

        return "".join([{'=':'-','+':'.','/':'_'}.get(c,c) for c in
                        digest.digest().encode('base64').rstrip('\n')])

class MusicBrainz:
    def __init__(self, server, port, messenger):
        self.server = server
        self.port = port
        self.connection = None
        self.messenger = messenger

    def connect(self):
        import httplib

        self.connection = httplib.HTTPConnection(self.server,self.port)

    def close(self):
        if (self.connection is not None):
            self.connection.close()

    #disc_id is a MBDiscID object
    #output is a file-like stream
    def read_data(self, disc_id, output):
        self.connection.request(
            "GET",
            "%s?%s" % ("/ws/1/release",
                       urllib.urlencode({"type":"xml","discid":str(disc_id)})))

        response = self.connection.getresponse()
        #FIXME - check for errors in the HTTP response
        #FIXME - throw exception if output is a "release not found" XML file
        #        (i.e. an empty release file)
        output.write(response.read())


#thrown if MusicBrainzReleaseXML.read() encounters an error
class MBXMLException(MetaDataFileException):
    def __unicode__(self):
        return _(u"Invalid MusicBrainz XML file")

class MusicBrainzReleaseXML:
    #dom should be a DOM object such as xml.dom.minidom.Document
    #of a MusicBrainz Release entry
    def __init__(self, dom):
        self.dom = dom

    @classmethod
    def read(cls, filename):
        from xml.dom.minidom import parse
        from xml.parsers.expat import ExpatError

        try:
            return cls(parse(filename))
        except (IOError,ExpatError):
            raise MBXMLException(filename)

    @classmethod
    def read_data(cls, data):
        from xml.dom.minidom import parseString
        from xml.parsers.expat import ExpatError

        try:
            return cls(parseString(data))
        except (IOError,ExpatError):
            raise MBXMLException(filename)

    def metadata(self):
        def get_nodes(parent,child_tag):
            return [node for node in parent.childNodes
                    if (hasattr(node,"tagName") and
                        (node.tagName == child_tag))]

        def get_text_node(parent, child_tag):
            try:
                return get_nodes(parent,child_tag)[0].childNodes[0].data
            except IndexError:
                return u''

        def get_track_metadata(track_node,
                               album_metadata,
                               track_number):
            try:
                #FIXME - not sure if name or sort-name should take precendence
                artist_name = get_text_node(get_nodes(track_node,u'artist')[0],
                                            u'name')
            except IndexError:
                artist_name = album_metadata.artist_name

            track_metadata = MetaData(track_name=get_text_node(track_node,
                                                               u'title'),
                                      artist_name=artist_name,
                                      track_number=track_number)

            track_metadata.merge(album_metadata)
            return track_metadata


        try:
            release = self.dom.getElementsByTagName(u'release')[0]
        except IndexError:
            return AlbumMetaData([])

        album_name = get_text_node(release,u'title')

        try:
            #FIXME - not sure if name or sort-name should take precendence
            artist_name = get_text_node(get_nodes(release,u'artist')[0],
                                        u'name')
        except IndexError:
            artist_name = u''

        try:
            tracks = get_nodes(get_nodes(release,u'track-list')[0],u'track')
        except IndexError:
            tracks = []

        album_metadata = MetaData(album_name=album_name,
                                  artist_name=artist_name,
                                  track_total=len(tracks))

        try:
            release_events = get_nodes(release,u'release-event-list')[0]
            event = get_nodes(release_events,u'event')[-1]
            album_metadata.year = event.getAttribute('date')[0:4]
            album_metadata.catalog = event.getAttribute('catalog-number')
        except IndexError:
            pass

        return AlbumMetaData([get_track_metadata(track_node=node,
                                                 album_metadata=album_metadata,
                                                 track_number=i + 1)
                              for (i,node) in enumerate(tracks)])
