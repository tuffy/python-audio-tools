# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

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


from audiotools import PY3
from audiotools._accuraterip import Checksum


class __Checksum__(object):
    """Python implementation of checksum calculator"""

    def __init__(self, total_pcm_frames,
                 sample_rate=44100,
                 is_first=False,
                 is_last=False,
                 pcm_frame_range=1):
        if total_pcm_frames <= 0:
            raise ValueError("total PCM frames must be > 0")
        if sample_rate <= 0:
            raise ValueError("sample rate must be > 0")
        if pcm_frame_range <= 0:
            raise ValueError("PCM frame range must be > 0")

        self.__total_pcm_frames__ = total_pcm_frames
        self.__pcm_frame_range__ = pcm_frame_range
        self.__values__ = []

        if is_first:
            self.__start_offset__ = ((sample_rate // 75) * 5)
        else:
            self.__start_offset__ = 1

        if is_last:
            self.__end_offset__ = (total_pcm_frames -
                                   ((sample_rate // 75) * 5))
        else:
            self.__end_offset__ = total_pcm_frames

    def update(self, framelist):
        from itertools import izip
        from audiotools.pcm import FrameList

        def value(l, r):
            return (unsigned(r) << 16) | unsigned(l)

        def unsigned(v):
            return (v if (v >= 0) else ((1 << 16) - (-v)))

        if not isinstance(framelist, FrameList):
            raise TypeError("framelist must be instance of Framelist")
        elif framelist.channels != 2:
            raise ValueError("FrameList must have 2 channels")
        elif framelist.bits_per_sample != 16:
            raise ValueError("FrameList must have 16 bits-per-sample")

        if ((len(self.__values__) +
             framelist.frames) > (self.__total_pcm_frames__ +
                                  self.__pcm_frame_range__ - 1)):
            raise ValueError("too many samples for checksum")

        self.__values__.extend(
            [value(l, r) for (l, r) in izip(framelist.channel(0),
                                            framelist.channel(1))])

    def checksums_v1(self):
        if (len(self.__values__) < (self.__total_pcm_frames__ +
                                    self.__pcm_frame_range__ - 1)):
            raise ValueError("insufficient samples for checksum")

        return [sum([(v * i) if
                     ((i >= self.__start_offset__) and
                      (i <= self.__end_offset__)) else 0
                     for (i, v) in
                     enumerate(self.__values__[r:
                                               r + self.__total_pcm_frames__],
                               1)]) & 0xFFFFFFFF
                for r in range(self.__pcm_frame_range__)]

    def checksums_v2(self):
        if (len(self.__values__) < (self.__total_pcm_frames__ +
                                    self.__pcm_frame_range__ - 1)):
            raise ValueError("insufficient samples for checksum")

        def combine(x):
            return (x >> 32) + (x & 0xFFFFFFFF)

        return [sum([combine(v * i) if
                     ((i >= self.__start_offset__) and
                      (i <= self.__end_offset__)) else 0
                     for (i, v) in
                     enumerate(self.__values__[r:
                                               r + self.__total_pcm_frames__],
                               1)]) & 0xFFFFFFFF
                for r in range(self.__pcm_frame_range__)]


def match_offset(ar_matches, checksums, initial_offset):
    """ar_matches is a list of (confidence, crc, crc2) tuples

    checksums is a list of calculated AccurateRip crcs

    initial_offset is the starting offset of the checksums

    returns (checksum, confidence, offset) of the best match found
    if no matches are found, confidence is None and offset is 0
    """

    if len(checksums) == 0:
        raise ValueError("at least 1 checksum is required")

    # crc should be unique in the list
    # but confidence may not be
    matches = {crc: confidence for (confidence, crc, crc2) in
               ar_matches}

    offsets = {crc: offset for (offset, crc) in
               enumerate(checksums, initial_offset)}

    match_offsets = sorted(
        [(crc, matches[crc], offsets[crc]) for crc in
         set(matches.keys()) & set(offsets.keys())],
        key=lambda triple: triple[1])

    if len(match_offsets) > 0:
        # choose the match with the highest confidence
        return match_offsets[-1]
    else:
        # no match found
        # return checksum at offset 0, or as close as possible
        if initial_offset <= 0:
            return (checksums[-initial_offset], None, 0)
        else:
            return (checksums[0], None, initial_offset)


class DiscID(object):
    def __init__(self, track_numbers, track_offsets,
                 lead_out_offset, freedb_disc_id):
        """track_numbers is a list of track numbers, starting from 1

        track_offsets is a list of offsets, in CD frames
        and typically starting from 0

        lead_out_offset is the offset of the lead-out track, in CD frames

        freedb_disc_id is a string or freedb.DiscID object of the CD
        """

        assert(len(track_numbers) == len(track_offsets))

        self.__track_numbers__ = track_numbers
        self.__track_offsets__ = track_offsets
        self.__lead_out_offset__ = lead_out_offset
        self.__freedb_disc_id__ = freedb_disc_id

    @classmethod
    def from_cddareader(cls, cddareader):
        """given a CDDAReader object, returns a DiscID for that object"""

        from audiotools.freedb import DiscID as FDiscID

        offsets = cddareader.track_offsets
        return cls(track_numbers=list(sorted(offsets.keys())),
                   track_offsets=[(offsets[k] // 588) for k in
                                  sorted(offsets.keys())],
                   lead_out_offset=cddareader.last_sector + 1,
                   freedb_disc_id=FDiscID.from_cddareader(cddareader))

    @classmethod
    def from_tracks(cls, tracks):
        """given a sorted list of AudioFile objects,
        returns DiscID for those tracks as if they were a CD"""

        from audiotools import has_pre_gap_track
        from audiotools.freedb import DiscID as FDiscID

        if not has_pre_gap_track(tracks):
            offsets = [0]
            for track in tracks[0:-1]:
                offsets.append(offsets[-1] + track.cd_frames())

            return cls(track_numbers=range(1, len(tracks) + 1),
                       track_offsets=offsets,
                       lead_out_offset=sum(t.cd_frames() for t in tracks),
                       freedb_disc_id=FDiscID.from_tracks(tracks))
        else:
            offsets = [tracks[0].cd_frames()]
            for track in tracks[1:-1]:
                offsets.append(offsets[-1] + track.cd_frames())

            return cls(track_numbers=range(1, len(tracks)),
                       track_offsets=offsets,
                       lead_out_offset=sum(t.cd_frames() for t in tracks),
                       freedb_disc_id=FDiscID.from_tracks(tracks))

    @classmethod
    def from_sheet(cls, sheet, total_pcm_frames, sample_rate):
        """given a Sheet object
        length of the album in PCM frames
        and sample rate of the disc,
        returns a DiscID for that CD"""

        from audiotools.freedb import DiscID as FDiscID

        return cls(track_numbers=range(1, len(sheet) + 1),
                   track_offsets=[(int(t.index(1).offset() * 75))
                                  for t in sheet],
                   lead_out_offset=total_pcm_frames * 75 // sample_rate,
                   freedb_disc_id=FDiscID.from_sheet(sheet,
                                                     total_pcm_frames,
                                                     sample_rate))

    def track_numbers(self):
        return self.__track_numbers__[:]

    def id1(self):
        return sum(self.__track_offsets__) + self.__lead_out_offset__

    def id2(self):
        return (sum([n * max(o, 1) for (n, o) in
                     zip(self.__track_numbers__, self.__track_offsets__)]) +
                (max(self.__track_numbers__) + 1) * self.__lead_out_offset__)

    def freedb_disc_id(self):
        return int(self.__freedb_disc_id__)

    if PY3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u"dBAR-{tracks:03d}-{id1:08x}-{id2:08x}-{freedb:08x}.bin".format(
            tracks=len(self.__track_numbers__),
            id1=self.id1(),
            id2=self.id2(),
            freedb=int(self.__freedb_disc_id__))

    def __repr__(self):
        return "AccurateRipDiscID({})".format(
            ", ".join(["{}={!r}".format(key, getattr(self, attr))
                        for (key, attr) in
                        [("track_numbers", "__track_numbers__"),
                         ("track_offsets", "__track_offsets__"),
                         ("lead_out_offset", "__lead_out_offset__"),
                         ("freedb_disc_id", "__freedb_disc_id__")]]))


def perform_lookup(disc_id,
                   accuraterip_server="www.accuraterip.com",
                   accuraterip_port=80):
    """performs web-based lookup using the given DiscID object
    and returns a dict of
    {track_number:[(confidence, crc, crc2), ...], ...}
    where track_number starts from 1

    may return a dict of empty lists if no AccurateRip entry is found

    may raise urllib2.HTTPError if an error occurs querying the server
    """

    from audiotools.bitstream import BitstreamReader
    try:
        from urllib.request import urlopen, URLError
    except ImportError:
        from urllib2 import urlopen, URLError

    matches = {n: [] for n in disc_id.track_numbers()}

    url = "http://{}:{}/accuraterip/{}/{}/{}/{}".format(accuraterip_server,
                                                        accuraterip_port,
                                                        str(disc_id)[16],
                                                        str(disc_id)[15],
                                                        str(disc_id)[14],
                                                        disc_id)

    try:
        response = BitstreamReader(urlopen(url), True)
    except URLError:
        # no CD found matching given parameters
        return matches

    try:
        while True:
            (track_count,
             id1,
             id2,
             freedb_disc_id) = response.parse("8u 32u 32u 32u")
            if (((id1 == disc_id.id1()) and
                 (id2 == disc_id.id2()) and
                 (freedb_disc_id == disc_id.freedb_disc_id()))):
                for track_number in range(1, track_count + 1):
                    if track_number in matches:
                        matches[track_number].append(
                            tuple(response.parse("8u 32u 32u")))
    except IOError:
        # keep trying to parse values until the data runs out
        response.close()
        return matches
