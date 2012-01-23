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

import audiotools

class DiscID:
    def __init__(self, first_track_number, last_track_number,
                 lead_out_offset, offsets):
        """first_track_number and last_track_number are ints
        typically starting from 1
        lead_out_offset is an integer number of CD frames
        offsets is a list of track offsets, in CD frames"""

        assert((last_track_number - first_track_number + 1) == len(offsets))

        self.first_track_number = first_track_number
        self.last_track_number = last_track_number
        self.lead_out_offset = lead_out_offset
        self.offsets = offsets

    def __repr__(self):
        return "DiscID(%s, %s, %s, %s)" % \
            (self.first_track_number,
             self.last_track_number,
             self.lead_out_offset,
             self.offsets)

    def __str__(self):
        from hashlib import sha1
        from base64 import b64encode

        return b64encode(
            sha1("%2.2X%2.2X%s" %
                 (self.first_track_number,
                  self.last_track_number,
                  "".join(["%8.8X" % (offset) for offset in
                           [self.lead_out_offset] +
                           self.offsets +
                           [0] * (99 - len(self.offsets))
                           ]))).digest(),
            "._").replace("=","-")

def perform_lookup(first_track_number, last_track_number,
                   lead_out_offset, offsets,
                   musicbrainz_server, musicbrainz_port):
    """performs a web-based lookup using
    first_track_number, last_track_number, lead_out_offset
    and a list of offset ints

    iterates over a tuple of MetaData objects per track
    where the first result are all the MetaData matches
    for the first track, etc.  in the event there
    are multiple results for a given disc

    may raise urllib2.HTTPError if an error occurs querying the server
    or ValueError if the server returns invalid data
    """

    raise NotImplementedError()

def parse_release(release, disc_id):
    """given a <release> DOM element and DiscID object
    yields a populated MetaData object per track"""

    def get_node(parent, *nodes):
        if (len(nodes) == 0):
            return parent
        else:
            for child in parent.childNodes:
                if (hasattr(child, "tagName") and (child.tagName == nodes[0])):
                    return get_node(child, *nodes[1:])
            else:
                raise KeyError(nodes[0])

    def text(node):
        if (node.firstChild is not None):
            return node.firstChild.data
        else:
            return u""

    #find album title in <title> tag
    try:
        album_name = text(get_node(release, u"title"))
    except KeyError:
        album_name = u""

    #find album artist(s) in <artist-credit> tag

    #find disc in <medium-list> tag

    #if multiple discs in <medium-list>,
    #populate album number and album total

    #find all <track> tags in <medium> tag's <track-list>

    #populate each track's title
    #and optional track-specific artist

    #yield complete MetaData object
