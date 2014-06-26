#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2014  Brian Langenberger

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


from audiotools._accuraterip import ChecksumV2


class ChecksumV1:
    def __init__(self, total_pcm_frames,
                 sample_rate=44100,
                 is_first=False,
                 is_last=False,
                 pcm_frame_range=1):
        if (total_pcm_frames <= 0):
            raise ValueError("total PCM frames must be > 0")
        if (sample_rate <= 0):
            raise ValueError("sample rate must be > 0")
        if (pcm_frame_range <= 0):
            raise ValueError("PCM frame range must be > 0")

        self.__total_pcm_frames__ = total_pcm_frames
        self.__pcm_frame_range__ = pcm_frame_range
        self.__i__ = 0
        self.__checksums__ = [0]
        self.__initial_values__ = []
        self.__final_values__ = []
        self.__values_sum__ = 0

        if (is_first):
            self.__start_offset__ = ((sample_rate // 75) * 5) - 1
        else:
            self.__start_offset__ = 0

        if (is_last):
            self.__end_offset__ = (total_pcm_frames -
                                   ((sample_rate // 75) * 5))
        else:
            self.__end_offset__ = total_pcm_frames

    def update(self, framelist):
        from itertools import izip

        def value(l, r):
            return (unsigned(r) << 16) | unsigned(l)

        def unsigned(v):
            return (v if (v >= 0) else ((1 << 16) - (-v)))

        if (framelist.channels != 2):
            raise ValueError("FrameList must have 2 channels")
        elif (framelist.bits_per_sample != 16):
            raise ValueError("FrameList must have 16 bits-per-sample")

        if ((self.__i__ + framelist.frames) >
            (self.__total_pcm_frames__ +
             self.__pcm_frame_range__ - 1)):
             raise ValueError("too many samples for checksum")

        for (i, (l, r)) in enumerate(izip(framelist.channel(0),
                                          framelist.channel(1)), self.__i__):
            v = value(l, r)

            #calculate initial checksum
            if ((i >= self.__start_offset__) and (i < self.__end_offset__)):
                if ((i - self.__start_offset__) <
                    (self.__pcm_frame_range__ - 1)):
                    self.__initial_values__.append(v)
                self.__checksums__[0] += (v * (i + 1))
                self.__values_sum__ += v
            elif ((i >= self.__end_offset__) and
                  ((i - self.__end_offset__) <
                   (self.__pcm_frame_range__ - 1))):
                self.__final_values__.append(v)

            #calculate incremental checksums
            if (i >= self.__total_pcm_frames__):
                j = i - self.__total_pcm_frames__
                self.__checksums__.append(
                    self.__checksums__[-1] +
                    (self.__end_offset__ * self.__final_values__[j]) -
                    self.__values_sum__ -
                    (self.__start_offset__ *
                     self.__initial_values__[j]))
                self.__values_sum__ -= self.__initial_values__[j]
                self.__values_sum__ += self.__final_values__[j]

        self.__i__ += framelist.frames

    def checksums(self):
        if (self.__i__ < ((self.__total_pcm_frames__ +
                           self.__pcm_frame_range__ - 1))):
            raise ValueError("insufficient samples for checksums")

        return [c & 0xFFFFFFFF for c in self.__checksums__]


class DiscID:
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

    def __str__(self):
        return "dBAR-%(tracks)3.3d-%(id1)8.8x-%(id2)8.8x-%(freedb)8.8x.bin" % \
            {"tracks": len(self.__track_numbers__),
             "id1": self.id1(),
             "id2": self.id2(),
             "freedb": int(self.__freedb_disc_id__)}

    def __repr__(self):
        return "AccurateRipDiscID(%s, %s, %s, %s)" % \
            (repr(self.__track_numbers__),
             repr(self.__track_offsets__),
             repr(self.__lead_out_offset__),
             repr(self.__freedb_disc_id__))


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

    from .bitstream import BitstreamReader
    from urllib2 import urlopen, URLError

    matches = dict([(n, []) for n in disc_id.track_numbers()])

    url = "http://%s:%s/accuraterip/%s/%s/%s/%s" % (accuraterip_server,
                                                    accuraterip_port,
                                                    str(disc_id)[16],
                                                    str(disc_id)[15],
                                                    str(disc_id)[14],
                                                    disc_id)

    try:
        response = BitstreamReader(urlopen(url), True)
    except URLError:
        #no CD found matching given parameters
        return matches

    try:
        while (True):
            (track_count,
             id1,
             id2,
             freedb_disc_id) = response.parse("8u 32u 32u 32u")
            if (((id1 == disc_id.id1()) and
                 (id2 == disc_id.id2()) and
                 (freedb_disc_id == disc_id.freedb_disc_id()))):
                for track_number in xrange(1, track_count + 1):
                    if (track_number in matches):
                        matches[track_number].append(
                            tuple(response.parse("8u 32u 32u")))
    except IOError:
        #keep trying to parse values until the data runs out
        return matches
