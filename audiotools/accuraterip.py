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


from . import DiscID

class AccurateRipDiscID:
    def __init__(self, offsets):
        """offsets is a list of CD track offsets, in CD sectors

        these offsets *do not* include the 150 sector lead-in"""

        self.__offsets__ = offsets

    def track_count(self):
        return len(self.__offsets__) - 1

    def id1(self):
        return sum(self.__offsets__)

    def id2(self):
        return sum([max(offset, 1) * (i + 1)
                    for (i, offset) in enumerate(self.__offsets__)])

    def id3(self):
        return DiscID(
            tracks=[y - x for (x,y) in zip(self.__offsets__,
                                           self.__offsets__[1:])],
            offsets=[offset + 150 for offset in self.__offsets__[0:-1]],
            length=self.__offsets__[-1])

    @classmethod
    def from_cdda(cls, cdda):
        return cls([cdda.cdda.track_offsets(i)[0] for i in
                    xrange(1, len(cdda) + 2)])

    @classmethod
    def from_tracks(cls, tracks):
        offsets = [0]
        for track in tracks:
            offsets.append(offsets[-1] + track.cd_frames())

        return cls(offsets)

    def db_filename(self):
        return ("dBAR-%(tracks)3.3d-%(id1)8.8x-%(id2)8.8x-%(id3)s.bin" %
                {"tracks":self.track_count(),
                 "id1":self.id1(),
                 "id2":self.id2(),
                 "id3":self.id3()})

    def url(self):
        id1 = self.id1()

        return ("http://www.accuraterip.com/accuraterip/%.1x/%.1x/%.1x/%s" %
                (id1 & 0xF,
                 (id1 >> 4) & 0xF,
                 (id1 >> 8) & 0xF,
                 self.db_filename()))

    def __repr__(self):
        return "AccurateRipDiscID(%s)" % (repr(self.__offsets__))


class AccurateRipEntry:
    # ACCURATERIP_DB_ENTRY = Con.GreedyRepeater(
    #     Con.Struct("db_entry",
    #                Con.ULInt8("track_count"),
    #                Con.ULInt32("disc_id1"),
    #                Con.ULInt32("disc_id2"),
    #                Con.ULInt32("freedb_id"),
    #                Con.StrictRepeater(lambda ctx: ctx["track_count"],
    #                                   Con.Struct("tracks",
    #                                              Con.ULInt8("confidence"),
    #                                              Con.ULInt32("crc"),
    #                                              Con.ULInt32("crc2")))))

    def __init__(self, disc_id1, disc_id2, freedb_id, track_entries):
        """disc_id1, disc_id2 and freedb_id are ints

        track_entries is a list of lists of AccurateRipTrackEntry objects"""

        self.disc_id1 = disc_id1
        self.disc_id2 = disc_id2
        self.freedb_id = freedb_id
        self.track_entries = track_entries

    def __repr__(self):
        return "AccurateRipEntry(%s, %s, %s, %s)" % \
            (repr(self.disc_id1),
             repr(self.disc_id2),
             repr(self.freedb_id),
             repr(self.track_entries))

    def __getitem__(self, key):
        #returns a list of 0 or more AccurateRipTrackEntry objects
        return self.track_entries[key]

    def __len__(self):
        return len(self.track_entries)

    @classmethod
    def parse_string(cls, string):
        """given a string, returns an AccurateRipEntry object"""

        entries = cls.ACCURATERIP_DB_ENTRY.parse(string)

        if (len(entries) == 0):
            raise ValueError("no AccurateRip entries found")

        #all disc IDs should be identical
        #and zip the track entries together
        return cls(
            disc_id1=entries[0].disc_id1,
            disc_id2=entries[0].disc_id2,
            freedb_id=entries[0].freedb_id,
            track_entries=[
                [AccurateRipTrackEntry(confidence=track.confidence,
                                       crc=track.crc,
                                       crc2=track.crc2) for track in tracks]
                for tracks in zip(*[entry.tracks for entry in entries])])

    @classmethod
    def from_disc_id(cls, disc_id):
        """given an AccurateRipDiscID, returns an AccurateRipEntry
        or None if the given disc ID has no matches in the database"""

        import urllib

        response = urllib.urlopen(disc_id.url())
        if (response.getcode() == 200):
            return cls.parse_string(response.read())
        else:
            return None


class AccurateRipTrackEntry:
    def __init__(self, confidence, crc, crc2):
        self.confidence = confidence  #heh
        self.crc = crc
        self.crc2 = crc2

    def __repr__(self):
        return "AccurateRipTrackEntry(%s, %s, %s)" % \
            (self.confidence,
             self.crc,
             self.crc2)

class AccurateRipTrackCRC:
    def __init__(self):
        self.crc = 0
        self.track_index = 1
        from .cdio import accuraterip_crc
        self.accuraterip_crc = accuraterip_crc

    def __int__(self):
        return self.crc

    def update(self, frame):
        (self.crc, self.track_index) = self.accuraterip_crc(self.crc,
                                                            self.track_index,
                                                            frame)
