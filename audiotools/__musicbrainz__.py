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

from audiotools import (MetaData, AlbumMetaData, AlbumMetaDataFile,
                        MetaDataFileException,
                        __most_numerous__, DummyAudioFile, sys)
import urllib
import gettext

gettext.install("audiotools", unicode=True)


def get_xml_nodes(parent, child_tag):
    """A helper routine for returning all children with the given XML tag."""

    return [node for node in parent.childNodes
            if (hasattr(node, "tagName") and
                (node.tagName == child_tag))]


def walk_xml_tree(parent, *child_tags):
    """A helper routine for walking through several children."""

    if (len(child_tags) == 0):
        return parent
    else:
        base_tag = child_tags[0]
        remaining_tags = child_tags[1:]
        for node in parent.childNodes:
            if (hasattr(node, "tagName") and
                (node.tagName == base_tag)):
                return walk_xml_tree(node, *remaining_tags)
        else:
            return None


def walk_xml_tree_build(dom, parent, *child_tags):

    if (len(child_tags) == 0):
        return parent
    else:
        base_tag = child_tags[0]
        remaining_tags = child_tags[1:]
        for node in parent.childNodes:
            if (hasattr(node, "tagName") and
                (node.tagName == base_tag)):
                return walk_xml_tree_build(dom, node, *remaining_tags)
        else:
            new_child = dom.createElement(base_tag)
            parent.appendChild(new_child)
            return walk_xml_tree_build(dom, new_child, *remaining_tags)


def get_xml_text_node(parent, child_tag):
    """A helper routine for returning the first text child XML node."""

    try:
        return get_xml_nodes(parent, child_tag)[0].childNodes[0].data.strip()
    except IndexError:
        return u''


def reorder_xml_children(parent, child_order):
    """Given an XML element with childNodes, reorders them to child_order.

    child_order should be a list of unicode tag strings.
    """

    if (parent.childNodes is None):
        return

    child_tags = {}
    leftovers = []
    for child in parent.childNodes:
        if (hasattr(child, "tagName")):
            child_tags.setdefault(child.tagName, []).append(child)
        else:
            leftovers.append(child)

    #remove all the old childen from parent
    for child in parent.childNodes:
        parent.removeChild(child)

    #re-add the childen in child_order
    for tagName in child_order:
        if (tagName in child_tags):
            for child in child_tags[tagName]:
                parent.appendChild(child)
            del(child_tags[tagName])

    #re-add any leftover children tags or non-tags
    for child_tags in child_tags.values():
        for child in child_tags:
            parent.appendChild(child)

    for child in leftovers:
        parent.appendChild(child)


class MBDiscID:
    """A MusicBrainz disc ID."""

    def __init__(self, tracks=[], offsets=None, length=None, lead_in=150,
                 first_track_number=None, last_track_number=None,
                 lead_out_track_offset=None):
        """Fields are as follows:

        tracks  - a list of track lengths in CD frames
        offsets -  a list of track offsets in CD frames
        length  - the length of the entire disc in CD frames
        lead_in - the location of the first track on the CD, in frames

        first_track_number, last_track_number and lead_out_track_offset
        are integer values.

        All fields are optional.
        One will presumably fill them with data later in that event.
        """

        self.tracks = tracks
        self.__offsets__ = offsets
        self.__length__ = length
        self.__lead_in__ = lead_in
        self.first_track_number = first_track_number
        self.last_track_number = last_track_number
        self.lead_out_track_offset = lead_out_track_offset

    @classmethod
    def from_cdda(cls, cdda):
        """Given a CDDA object, returns a populated MBDiscID

        May raise ValueError if there are no audio tracks on the CD."""

        tracks = list(cdda)
        if (len(tracks) < 1):
            raise ValueError(_(u"no audio tracks in CDDA object"))

        return cls(
            tracks=[t.length() for t in tracks],
            offsets=[t.offset() for t in tracks],
            length=cdda.length(),
            lead_in=tracks[0].offset(),
            lead_out_track_offset=cdda.last_sector() + 150 + 1)

    def offsets(self):
        """Returns a list of calculated offset integers, from track lengths."""

        if (self.__offsets__ is None):
            offsets = [self.__lead_in__]

            for track in self.tracks[0:-1]:
                offsets.append(track + offsets[-1])

            return offsets
        else:
            return self.__offsets__

    def __repr__(self):
        return ("MBDiscID(tracks=%s,offsets=%s,length=%s,lead_in=%s," +
                "first_track_number=%s,last_track_number=%s," +
                "lead_out_track_offset=%s)") % \
            (repr(self.tracks),
             repr(self.__offsets__),
             repr(self.__length__),
             repr(self.__lead_in__),
             repr(self.first_track_number),
             repr(self.last_track_number),
             repr(self.lead_out_track_offset))

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

        return "".join([{'=': '-', '+': '.', '/': '_'}.get(c, c) for c in
                        digest.digest().encode('base64').rstrip('\n')])

    def toxml(self, output):
        """Writes an XML file to the output file object."""

        output.write(MusicBrainzReleaseXML.from_tracks(
                [DummyAudioFile(length, None, i + 1)
                 for (i, length) in enumerate(self.tracks)]).to_string())


class MusicBrainz:
    """A class for performing queries on a MusicBrainz or compatible server."""

    def __init__(self, server, port, messenger):
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

    def read_data(self, disc_id, output):
        """Returns a (matches,dom) tuple from a MBDiscID object.

        matches is an integer
        and dom is a minidom Document object or None."""

        from xml.dom.minidom import parseString
        from xml.parsers.expat import ExpatError

        self.connection.request(
            "GET",
            "%s?%s" % ("/ws/1/release",
                       urllib.urlencode({"type": "xml",
                                         "discid": str(disc_id)})))

        response = self.connection.getresponse()
        #FIXME - check for errors in the HTTP response

        data = response.read()

        try:
            dom = parseString(data)
            return (len(dom.getElementsByTagName(u'release')), dom)
        except ExpatError:
            return (0, None)


class MBXMLException(MetaDataFileException):
    """Raised if MusicBrainzReleaseXML.read() encounters an error."""

    def __unicode__(self):
        return _(u"Invalid MusicBrainz XML file")


class MusicBrainzReleaseXML(AlbumMetaDataFile):
    """An XML file as returned by MusicBrainz."""

    TAG_ORDER = {u"release": [u"title",
                              u"text-representation",
                              u"asin",
                              u"artist",
                              u"release-group",
                              u"release-event-list",
                              u"disc-list",
                              u"puid-list",
                              u"track-list",
                              u"relation-list",
                              u"tag-list",
                              u"user-tag-list",
                              u"rating",
                              u"user-rating"],
                 u"artist": [u"name",
                             u"sort-name",
                             u"disambiguation",
                             u"life-span",
                             u"alias-list",
                             u"release-list",
                             u"release-group-list",
                             u"relation-list",
                             u"tag-list",
                             u"user-tag-list",
                             u"rating"],
                 u"track": [u"title",
                            u"duration",
                            u"isrc-list",
                            u"artist",
                            u"release-list",
                            u"puid-list",
                            u"relation-list",
                            u"tag-list",
                            u"user-tag-list",
                            u"rating",
                            u"user-rating"]}

    def __init__(self, dom):
        self.dom = dom

    def __getattr__(self, key):
        if (key == 'album_name'):
            try:
                return get_xml_text_node(
                    walk_xml_tree(self.dom,
                                  u'metadata', u'release-list', u'release'),
                    u'title')
            except AttributeError:
                return u""
        elif (key == 'artist_name'):
            try:
                return get_xml_text_node(
                    walk_xml_tree(self.dom,
                                  u'metadata', u'release-list', u'release',
                                  u'artist'),
                    u'name')
            except AttributeError:
                return u""
        elif (key == 'year'):
            try:
                return walk_xml_tree(
                    self.dom, u'metadata', u'release-list', u'release',
                    u'release-event-list',
                    u'event').getAttribute('date')[0:4]
            except (IndexError, AttributeError):
                return u""
        elif (key == 'catalog'):
            try:
                return walk_xml_tree(
                    self.dom, u'metadata', u'release-list', u'release',
                    u'release-event-list',
                    u'event').getAttribute('catalog-number')
            except (IndexError, AttributeError):
                return u""
        elif (key == 'extra'):
            return u""
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __setattr__(self, key, value):
        #FIXME - create nodes if they don't exist
        if (key == 'album_name'):
            title = walk_xml_tree(self.dom, u'metadata', u'release-list',
                                  u'release', u'title')
            if (len(title.childNodes) > 0):
                title.replaceChild(self.dom.createTextNode(value),
                                   title.firstChild)
            else:
                title.appendChild(self.dom.createTextNode(value))
        elif (key == 'artist_name'):
            name = walk_xml_tree(self.dom, u'metadata', u'release-list',
                                 u'release', u'artist', u'name')
            if (len(name.childNodes) > 0):
                name.replaceChild(self.dom.createTextNode(value),
                                  name.firstChild)
            else:
                name.appendChild(self.dom.createTextNode(value))
        elif (key == 'year'):
            walk_xml_tree_build(self.dom, self.dom,
                                u'metadata', u'release-list',
                                u'release', u'release-event-list',
                                u'event').setAttribute(u"date", value)
        elif (key == 'catalog'):
            walk_xml_tree_build(self.dom, self.dom,
                                u'metadata', u'release-list',
                                u'release', u'release-event-list',
                                u'event').setAttribute(u"catalog-number",
                                                       value)
        elif (key == 'extra'):
            pass
        else:
            self.__dict__[key] = value

    def __len__(self):
        return len(self.dom.getElementsByTagName(u'track'))

    def to_string(self):
        for (tag, order) in MusicBrainzReleaseXML.TAG_ORDER.items():
            for parent in self.dom.getElementsByTagName(tag):
                reorder_xml_children(parent, order)

        return self.dom.toxml(encoding='utf-8')

    @classmethod
    def from_string(cls, string):
        from xml.dom.minidom import parseString
        from xml.parsers.expat import ExpatError

        try:
            return cls(parseString(string))
        except ExpatError:
            raise MBXMLException("")

    def get_track(self, index):
        track_node = self.dom.getElementsByTagName(u'track')[index]
        track_name = get_xml_text_node(track_node, u'title')
        artist_node = walk_xml_tree(track_node, u'artist')
        if (artist_node is not None):
            artist_name = get_xml_text_node(artist_node, u'name')
            if (len(artist_name) == 0):
                artist_name = u""
        else:
            artist_name = u""
        return (track_name, artist_name, u"")

    def set_track(self, index, name, artist, extra):
        track_node = self.dom.getElementsByTagName(u'track')[index]
        title = walk_xml_tree(track_node, 'title')
        if (len(title.childNodes) > 0):
            title.replaceChild(self.dom.createTextNode(name),
                               title.firstChild)
        else:
            title.appendChild(self.dom.createTextNode(name))
        if (len(artist) > 0):
            artist_node = walk_xml_tree_build(self.dom,
                                              track_node,
                                              u'artist', u'name')
            if (artist_node.hasChildNodes()):
                artist_node.replaceChild(self.dom.createTextNode(artist),
                                         artist_node.firstChild)
            else:
                artist_node.appendChild(self.dom.createTextNode(artist))

    @classmethod
    def from_tracks(cls, tracks):
        """Returns a MusicBrainzReleaseXML from a list of AudioFile objects.

        These objects are presumably from the same album.
        If not, these heuristics may generate something unexpected.
        """

        from xml.dom.minidom import parseString

        def make_text_node(document, tagname, text):
            node = document.createElement(tagname)
            node.appendChild(document.createTextNode(text))
            return node

        tracks.sort(lambda x, y: cmp(x.track_number(), y.track_number()))

        #our base DOM to start with
        dom = parseString('<?xml version="1.0" encoding="UTF-8"?>' +
                          '<metadata xmlns="http://musicbrainz.org/' +
                          'ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/' +
                          'ns/ext-1.0#"></metadata>')

        release = dom.createElement(u'release')

        track_metadata = [t.get_metadata() for t in tracks
                          if (t.get_metadata() is not None)]

        #add album title
        release.appendChild(make_text_node(
                dom, u'title', unicode(__most_numerous__(
                        [m.album_name for m in track_metadata]))))

        #add album artist
        if (len(set([m.artist_name for m in track_metadata])) <
            len(track_metadata)):
            artist = dom.createElement(u'artist')
            album_artist = unicode(__most_numerous__(
                    [m.artist_name for m in track_metadata]))
            artist.appendChild(make_text_node(dom, u'name', album_artist))
            release.appendChild(artist)
        else:
            album_artist = u''  # all track artist names differ
            artist = dom.createElement(u'artist')
            artist.appendChild(make_text_node(dom, u'name', album_artist))
            release.appendChild(artist)

        #add release info (catalog number, release date, media, etc.)
        event_list = dom.createElement(u'release-event-list')
        event = dom.createElement(u'event')

        year = unicode(__most_numerous__(
                [m.year for m in track_metadata]))
        if (year != u""):
            event.setAttribute(u'date', year)

        catalog_number = unicode(__most_numerous__(
                [m.catalog for m in track_metadata]))
        if (catalog_number != u""):
            event.setAttribute(u'catalog-number', catalog_number)

        media = unicode(__most_numerous__(
                [m.media for m in track_metadata]))
        if (media != u""):
            event.setAttribute(u'format', media)

        event_list.appendChild(event)
        release.appendChild(event_list)

        #add tracks
        track_list = dom.createElement(u'track-list')

        for track in tracks:
            node = dom.createElement(u'track')
            track_metadata = track.get_metadata()
            if (track_metadata is not None):
                node.appendChild(make_text_node(
                        dom, u'title', track_metadata.track_name))
            else:
                node.appendChild(make_text_node(
                        dom, u'title', u''))

            node.appendChild(make_text_node(
                    dom, u'duration',
                    unicode((track.total_frames() * 1000) /
                            track.sample_rate())))

            if (track_metadata is not None):
                #add track artist, if different from album artist
                if (track_metadata.artist_name != album_artist):
                    artist = dom.createElement(u'artist')
                    artist.appendChild(make_text_node(
                            dom, u'name', track_metadata.artist_name))
                    node.appendChild(artist)

            track_list.appendChild(node)

        release.appendChild(track_list)

        release_list = dom.createElement(u'release-list')
        release_list.appendChild(release)
        dom.getElementsByTagName(u'metadata')[0].appendChild(release_list)

        return cls(dom)


#takes a Document containing multiple <release> tags
#and a Messenger object to query for output
#returns a modified Document containing only one <release>
def __select_match__(dom, messenger):
    messenger.info(_(u"Please Select the Closest Match:"))
    matches = dom.getElementsByTagName(u'release')
    selected = 0
    while ((selected < 1) or (selected > len(matches))):
        for i in range(len(matches)):
            messenger.info(_(u"%(choice)s) %(name)s") % \
                               {"choice": i + 1,
                                "name": get_xml_text_node(matches[i],
                                                          u'title')})
        try:
            messenger.partial_info(_(u"Your Selection [1-%s]:") % \
                                       (len(matches)))
            selected = int(sys.stdin.readline().strip())
        except ValueError:
            selected = 0

    for (i, release) in enumerate(dom.getElementsByTagName(u'release')):
        if (i != (selected - 1)):
            release.parentNode.removeChild(release)

    return dom


#takes a Document containing multiple <release> tags
#and a default selection integer
#returns a modified Document containing only one <release>
def __select_default_match__(dom, selection):
    for (i, release) in enumerate(dom.getElementsByTagName(u'release')):
        if (i != selection):
            release.parentNode.removeChild(release)

    return dom


def get_mbxml(disc_id, output, musicbrainz_server, musicbrainz_port,
              messenger, default_selection=None):
    """Runs through the entire MusicBrainz querying sequence.

    Fields are as follows:
    disc_id            - an MBDiscID object
    output             - an open file object for writing
    musicbrainz_server - a server name string
    musicbrainz_port   - a server port int
    messenger          - a Messenger object
    default_selection  - if given, the default match to choose
    """

    mb = MusicBrainz(musicbrainz_server, musicbrainz_port, messenger)

    mb.connect()
    messenger.info(
        _(u"Sending Disc ID \"%(disc_id)s\" to server \"%(server)s\"") % \
            {"disc_id": str(disc_id).decode('ascii'),
             "server": musicbrainz_server.decode('ascii', 'replace')})

    (matches, dom) = mb.read_data(disc_id, output)
    mb.close()

    if (matches == 1):
        messenger.info(_(u"1 match found"))
    else:
        messenger.info(_(u"%s matches found") % (matches))

    if (matches > 1):
        if (default_selection is None):
            output.write(__select_match__(
                    dom, messenger).toxml(encoding='utf-8'))
        else:
            output.write(__select_default_match__(
                    dom, default_selection).toxml(encoding='utf-8'))

        output.flush()
    elif (matches == 1):
        output.write(dom.toxml(encoding='utf-8'))
        output.flush()
    else:
        return matches
