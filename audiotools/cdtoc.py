# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2016  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from audiotools import PY3, Sheet, SheetTrack, SheetIndex


class CDTOC(Sheet):
    """an object representing a CDDA layout as a Vorbis comment tag"""

    def __init__(self, cdtoc_tracks, lead_out):
        """cdtoc_tracks is a list of CDTOC_Track objects
        lead_out is the address of the lead out"""

        self.__cdtoc_tracks__ = cdtoc_tracks
        self.__lead_out__ = lead_out

    def __repr__(self):
        return "CDTOC({!r}, {!r})".format(self.__cdtoc_tracks__,
                                          self.__lead_out__)

    if PY3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u"+".join([u"{:X}".format(
                         len([t for t in self if t.is_audio()]))] +
                         [t.__unicode__() for t in self] +
                         [u"{:X}".format(self.__lead_out__)])

    @classmethod
    def from_unicode(cls, u):
        """given a Unicode string, returns a CDTOC
        may raise ValueError if a parsing problem occurs"""

        items = u.split(u"+")
        track_count = int(items[0], 16)
        audio_track_addresses = [int(i, 16) for i in items[1:1 + track_count]]
        remaining_items = items[1 + track_count:]

        if len(remaining_items) == 1:
            # all audio tracks
            lead_out_address = int(remaining_items[0], 16)
            return cls([CDTOC_Track(i, address) for (i, address) in
                       enumerate(audio_track_addresses, 1)],
                       lead_out_address)
        elif len(remaining_items) == 2:
            # might be CDExtra or Data+Audio
            if remaining_items[1].startswith(u"X"):
                # Data+Audio
                lead_out_address = int(remaining_items[0], 16)
                data_track_address = int(remaining_items[1][1:], 16)
                return CDTOC_DataAudio(
                    [CDTOC_Track(1,
                                 data_track_address,
                                 False)] +
                    [CDTOC_Track(i, address) for (i, address) in
                     enumerate(audio_track_addresses, 2)],
                    lead_out_address)
            else:
                # CDExtra
                data_track_address = int(remaining_items[0], 16)
                lead_out_address = int(remaining_items[1], 16)
                return cls([CDTOC_Track(i, address) for (i, address) in
                            enumerate(audio_track_addresses, 1)] +
                           [CDTOC_Track(track_count + 1,
                                        data_track_address,
                                        False)],
                           lead_out_address)
        else:
            raise ValueError("too many items")

    @classmethod
    def converted(cls, sheet, seconds_length):
        """given a Sheet-compatible object
        and length of entire disc as a Fractional number of seconds,
        returns a CDTOC"""

        sheet_tracks = list(sheet)
        is_audio = [t.is_audio() for t in sheet_tracks]
        if False not in is_audio:
            # all tracks are audio, so not CDExtra or Data+Audio
            return cls([CDTOC_Track.converted(t) for t in sheet_tracks],
                       int(seconds_length * 75) + 150)
        elif (not is_audio[0]) and (False not in is_audio[1:]):
            # Data+Audio
            return CDTOC_DataAudio(
                [CDTOC_Track.converted(t) for t in sheet_tracks],
                int(seconds_length * 75) + 150)
        elif (False not in is_audio[0:-1]) and not is_audio[-1]:
            # CDExtra
            return cls([CDTOC_Track.converted(t) for t in sheet_tracks],
                       int(seconds_length * 75) + 150)
        else:
            raise ValueError("unsupported Sheet layout")

    def __len__(self):
        return len(self.__cdtoc_tracks__)

    def __getitem__(self, index):
        return self.__cdtoc_tracks__[index]

    def track_length(self, track_number, total_length=None):
        """given a track_number (typically starting from 1)
        and optional total length as a Fraction number of seconds
        (including the disc's pre-gap, if any),
        returns the length of the track as a Fraction number of seconds
        or None if the length is to the remainder of the stream
        (typically for the last track in the album)

        may raise KeyError if the track is not found"""

        initial_track = self.track(track_number)
        if track_number < len(self):
            next_track = self.track(track_number + 1)
            return (next_track.index(1).offset() -
                    initial_track.index(1).offset())
        else:
            # no next track, so return to end of lead-out
            from fractions import Fraction
            return (Fraction(self.__lead_out__ - 150, 75) -
                    initial_track.index(1).offset())

    def get_metadata(self):
        return None


class CDTOC_DataAudio(CDTOC):
    def __init__(self, cdtoc_tracks, lead_out):
        """cdtoc_tracks is a list of CDTOC_Track objects
        lead_out is the address of the lead out"""

        # first track must be non-audio, rest must be audio
        assert(not cdtoc_tracks[0].is_audio())
        assert(False not in [t.is_audio() for t in cdtoc_tracks[1:]])

        CDTOC.__init__(self, cdtoc_tracks, lead_out)

    def __unicode__(self):
        return u"+".join([u"{:X}".format(len(self) - 1)] +
                         [t.__unicode__() for t in self[1:]] +
                         [u"{:X}".format(self.__lead_out__),
                          u"X{}".format(self[0].__unicode__())])

    def __repr__(self):
        return "CDTOC_DataAudio({!r}, {!r})".format(self.__cdtoc_tracks__,
                                                    self.__lead_out__)


class CDTOC_Track(SheetTrack):
    def __init__(self, number, address, is_audio=True):
        """number is the track number, starting from 1
        address is the track's LBA + 150 value
        is_audio determines whether the track contains audio data"""

        self.__number__ = number
        if (number == 1) and (address > 150):
            # add index point 0 as pre-gap
            self.__indexes__ = [CDTOC_Index(0, 150), CDTOC_Index(1, address)]
        else:
            self.__indexes__ = [CDTOC_Index(1, address)]
        self.__is_audio__ = is_audio

    @classmethod
    def converted(cls, sheet_track):
        """given a SheetTrack object, returns a CDTOC_Track"""

        index_1 = sheet_track.index(1).offset()
        return cls(sheet_track.number(),
                   int(index_1 * 75) + 150,
                   sheet_track.is_audio())

    def __len__(self):
        return len(self.__indexes__)

    def __getitem__(self, i):
        return self.__indexes__[i]

    if PY3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return self.index(1).__unicode__()

    def __repr__(self):
        return "CDTOC_Track({!r}, {!r}, {!r})".format(
            self.__number__, self.__indexes__, self.__is_audio__)

    def number(self):
        """return SheetTrack's number, starting from 1"""

        return self.__number__

    def get_metadata(self):
        """returns SheetTrack's MetaData, or None"""

        return None

    def filename(self):
        """returns SheetTrack's filename as unicode"""

        return u"CDImage.wav"

    def is_audio(self):
        """returns whether SheetTrack contains audio data"""

        return self.__is_audio__

    def pre_emphasis(self):
        """returns whether SheetTrack has pre-emphasis"""

        return False

    def copy_permitted(self):
        """returns whether copying is permitted"""

        return False


class CDTOC_Index(SheetIndex):
    def __init__(self, number, address):
        self.__number__ = number
        self.__address__ = address

    if PY3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u"{:X}".format(self.__address__)

    def __repr__(self):
        return "CDTOC_Index(number={!r}, address={!r})".format(
            self.__number__, self.__address__)

    def number(self):
        return self.__number__

    def offset(self):
        from fractions import Fraction

        return Fraction(self.__address__ - 150, 75)
