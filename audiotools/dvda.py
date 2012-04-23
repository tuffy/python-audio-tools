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


class DVDAudio:
    """an object representing an entire DVD-Audio disc

    a DVDAudio object contains one or more DVDATitle objects
    (accessible via the .titlesets attribute)
    typically, only the first DVDTitle is interesting
    each DVDATitle then contains one or more DVDATrack objects
    """

    SECTOR_SIZE = 2048
    PTS_PER_SECOND = 90000

    def __init__(self, audio_ts_path, cdrom_device=None):
        """a DVD-A which contains PCMReader-compatible track objects"""

        import re
        import os
        import os.path

        self.audio_ts_path = audio_ts_path
        self.cdrom_device = cdrom_device

        #an inventory of AUDIO_TS files converted to uppercase keys
        self.files = dict([(name.upper(),
                            os.path.join(audio_ts_path, name))
                           for name in os.listdir(audio_ts_path)])

        titleset_numbers = list(self.__titlesets__())

        #for each titleset, read an ATS_XX_0.IFO file
        #each titleset contains one or more DVDATitle objects
        #and each DVDATitle object contains one or more DVDATrack objects
        self.titlesets = [self.__titles__(titleset) for titleset in
                          titleset_numbers]

        #for each titleset, calculate the lengths of the corresponding AOBs
        #in terms of 2048 byte sectors
        self.aob_sectors = []
        for titleset in titleset_numbers:
            aob_re = re.compile("ATS_%2.2d_\\d\\.AOB" % (titleset))
            titleset_aobs = dict([(key, value) for (key, value) in
                                  self.files.items()
                                  if (aob_re.match(key))])
            for aob_length in [os.path.getsize(titleset_aobs[key]) /
                               DVDAudio.SECTOR_SIZE
                               for key in sorted(titleset_aobs.keys())]:
                if (len(self.aob_sectors) == 0):
                    self.aob_sectors.append(
                        (0, aob_length))
                else:
                    self.aob_sectors.append(
                        (self.aob_sectors[-1][1],
                         self.aob_sectors[-1][1] + aob_length))

    def __getitem__(self, key):
        return self.titlesets[key]

    def __len__(self):
        return len(self.titlesets)

    def __titlesets__(self):
        """return valid audio titleset integers from AUDIO_TS.IFO"""

        from .bitstream import BitstreamReader

        try:
            f = open(self.files['AUDIO_TS.IFO'], 'rb')
        except (KeyError, IOError):
            raise InvalidDVDA(_(u"unable to open AUDIO_TS.IFO"))
        try:
            (identifier,
             AMG_start_sector,
             AMGI_end_sector,
             DVD_version,
             volume_count,
             volume_number,
             disc_side,
             autoplay,
             ts_to_sv,
             video_titlesets,
             audio_titlesets,
             provider_information) = BitstreamReader(f, 0).parse(
                "12b 32u 12P 32u 16u 4P 16u 16u 8u 4P 8u 32u 10P 8u 8u 40b")

            if (identifier != 'DVDAUDIO-AMG'):
                raise InvalidDVDA(_(u"invalid AUDIO_TS.IFO"))

            for titleset in xrange(1, audio_titlesets + 1):
                #ensure there are IFO files and AOBs
                #for each valid titleset
                if (("ATS_%2.2d_0.IFO" % (titleset) in
                     self.files.keys()) and
                    ("ATS_%2.2d_1.AOB" % (titleset) in
                     self.files.keys())):
                    yield titleset
        finally:
            f.close()

    def __titles__(self, titleset):
        """returns a list of DVDATitle objects for the given titleset"""

        #this requires bouncing all over the ATS_XX_0.IFO file

        import os
        from .bitstream import BitstreamReader

        try:
            f = open(self.files['ATS_%2.2d_0.IFO' % (titleset)], 'rb')
        except (KeyError, IOError):
            raise InvalidDVDA(
                _(u"unable to open ATS_%2.2d_0.IFO") % (titleset))
        try:
            #ensure the file's identifier is correct
            #which is all we care about from the first sector
            if (f.read(12) != 'DVDAUDIO-ATS'):
                raise InvalidDVDA(_(u"invalid ATS_%2.2d_0.IFO") % (titleset))

            #seek to the second sector and read the title count
            #and list of title table offset values
            f.seek(DVDAudio.SECTOR_SIZE, os.SEEK_SET)
            ats_reader = BitstreamReader(f, 0)
            (title_count, last_byte_address) = ats_reader.parse("16u 16p 32u")
            title_offsets = [ats_reader.parse("8u 24p 32u")[1] for title in
                             xrange(title_count)]

            titles = []

            for (title_number, title_offset) in enumerate(title_offsets):
                #for each title, seek to its title table
                #and read the title's values and its track timestamps
                f.seek(DVDAudio.SECTOR_SIZE + title_offset, os.SEEK_SET)
                ats_reader = BitstreamReader(f, 0)
                (tracks,
                 indexes,
                 track_length,
                 sector_pointers_table) = ats_reader.parse(
                    "16p 8u 8u 32u 4P 16u 2P")
                timestamps = [ats_reader.parse("32p 8u 8p 32u 32u 48p")
                              for track in xrange(tracks)]

                #seek to the title's sector pointers table
                #and read the first and last sector values for title's tracks
                f.seek(DVDAudio.SECTOR_SIZE +
                       title_offset +
                       sector_pointers_table,
                       os.SEEK_SET)
                ats_reader = BitstreamReader(f, 0)
                sector_pointers = [ats_reader.parse("32u 32u 32u")
                                   for i in xrange(indexes)]
                if ((len(sector_pointers) > 1) and
                    (set([p[0] for p in sector_pointers[1:]]) !=
                     set([0x01000000]))):
                    raise InvalidDVDA(_(u"invalid sector pointer"))
                else:
                    sector_pointers = [None] + sector_pointers

                #build a preliminary DVDATitle object
                #which we'll populate with track data
                dvda_title = DVDATitle(dvdaudio=self,
                                       titleset=titleset,
                                       title=title_number + 1,
                                       pts_length=track_length,
                                       tracks=[])

                #for each track, determine its first and last sector
                #based on the sector pointers between the track's
                #initial index and the next track's initial index
                for (track_number,
                     (timestamp,
                      next_timestamp)) in enumerate(zip(timestamps,
                                                        timestamps[1:])):
                    (index_number, first_pts, pts_length) = timestamp
                    next_timestamp_index = next_timestamp[0]
                    dvda_title.tracks.append(
                        DVDATrack(
                            dvdaudio=self,
                            titleset=titleset,
                            title=dvda_title,
                            track=track_number + 1,
                            first_pts=first_pts,
                            pts_length=pts_length,
                            first_sector=sector_pointers[index_number][1],
                            last_sector=sector_pointers[
                                next_timestamp_index - 1][2]))

                #for the last track, its sector pointers
                #simply consume what remains on the list
                (index_number, first_pts, pts_length) = timestamps[-1]
                dvda_title.tracks.append(
                    DVDATrack(
                        dvdaudio=self,
                        titleset=titleset,
                        title=dvda_title,
                        track=len(timestamps),
                        first_pts=first_pts,
                        pts_length=pts_length,
                        first_sector=sector_pointers[index_number][1],
                        last_sector=sector_pointers[-1][2]))

                #fill in the title's info such as sample_rate, channels, etc.
                dvda_title.__parse_info__()

                titles.append(dvda_title)

            return titles
        finally:
            f.close()


class InvalidDVDA(Exception):
    pass


class DVDATitle:
    """an object representing a DVD-Audio title

    contains one or more DVDATrack objects
    which may are accessible via __getitem__
    """

    def __init__(self, dvdaudio, titleset, title, pts_length, tracks):
        """length is in PTS ticks, tracks is a list of DVDATrack objects"""

        self.dvdaudio = dvdaudio
        self.titleset = titleset
        self.title = title
        self.pts_length = pts_length
        self.tracks = tracks

        self.sample_rate = 0
        self.channels = 0
        self.channel_mask = 0
        self.bits_per_sample = 0
        self.stream_id = 0

    def __parse_info__(self):
        """generates a cache of sample_rate, bits-per-sample, etc"""

        import re
        import os.path
        from .bitstream import BitstreamReader

        if (len(self.tracks) == 0):
            return

        #Why is this post-init processing necessary?
        #DVDATrack references DVDATitle
        #so a DVDATitle must exist when DVDATrack is initialized.
        #But because reading this info requires knowing the sector
        #of the first track, we wind up with a circular dependency.
        #Doing a "post-process" pass fixes that problem.

        #find the AOB file of the title's first track
        track_sector = self[0].first_sector
        titleset = re.compile("ATS_%2.2d_\\d\\.AOB" % (self.titleset))
        for aob_path in sorted([self.dvdaudio.files[key] for key in
                           self.dvdaudio.files.keys()
                           if (titleset.match(key))]):
            aob_sectors = os.path.getsize(aob_path) / DVDAudio.SECTOR_SIZE
            if (track_sector > aob_sectors):
                track_sector -= aob_sectors
            else:
                break
        else:
            raise ValueError(_(u"unable to find track sector in AOB files"))

        #open that AOB file and seek to that track's first sector
        aob_file = open(aob_path, 'rb')
        try:
            aob_file.seek(track_sector * DVDAudio.SECTOR_SIZE)
            aob_reader = BitstreamReader(aob_file, 0)

            #read and validate the pack header
            #(there's one pack header per sector, at the sector's start)
            (sync_bytes,
             marker1,
             current_pts_high,
             marker2,
             current_pts_mid,
             marker3,
             current_pts_low,
             marker4,
             scr_extension,
             marker5,
             bit_rate,
             marker6,
             stuffing_length) = aob_reader.parse(
                "32u 2u 3u 1u 15u 1u 15u 1u 9u 1u 22u 2u 5p 3u")
            aob_reader.skip_bytes(stuffing_length)
            if (sync_bytes != 0x1BA):
                raise InvalidDVDA(_(u"invalid AOB sync bytes"))
            if ((marker1 != 1) or (marker2 != 1) or (marker3 != 1) or
                (marker4 != 1) or (marker5 != 1) or (marker6 != 3)):
                raise InvalidDVDA(_(u"invalid AOB marker bits"))
            packet_pts = ((current_pts_high << 30) |
                          (current_pts_mid << 15) |
                          current_pts_low)

            #skip packets until one with a stream ID of 0xBD is found
            (start_code,
             stream_id,
             packet_length) = aob_reader.parse("24u 8u 16u")
            if (start_code != 1):
                raise InvalidDVDA(_(u"invalid AOB packet start code"))
            while (stream_id != 0xBD):
                aob_reader.skip_bytes(packet_length)
                (start_code,
                 stream_id,
                 packet_length) = aob_reader.parse("24u 8u 16u")
                if (start_code != 1):
                    raise InvalidDVDA(_(u"invalid AOB packet start code"))

            #parse the PCM/MLP header in the packet data
            (pad1_size,) = aob_reader.parse("16p 8u")
            aob_reader.skip_bytes(pad1_size)
            (stream_id, crc) = aob_reader.parse("8u 8u 8p")
            if (stream_id == 0xA0):  # PCM
                #read a PCM reader
                (pad2_size,
                 first_audio_frame,
                 padding2,
                 group1_bps,
                 group2_bps,
                 group1_sample_rate,
                 group2_sample_rate,
                 padding3,
                 channel_assignment) = aob_reader.parse(
                    "8u 16u 8u 4u 4u 4u 4u 8u 8u")
            else:                    # MLP
                aob_reader.skip_bytes(aob_reader.read(8))  # skip pad2
                #read a total frame size + MLP major sync header
                (total_frame_size,
                 sync_words,
                 stream_type,
                 group1_bps,
                 group2_bps,
                 group1_sample_rate,
                 group2_sample_rate,
                 unknown1,
                 channel_assignment,
                 unknown2) = aob_reader.parse(
                    "4p 12u 16p 24u 8u 4u 4u 4u 4u 11u 5u 48u")

            #return the values indicated by the header
            self.sample_rate = DVDATrack.SAMPLE_RATE[group1_sample_rate]
            self.channels = DVDATrack.CHANNELS[channel_assignment]
            self.channel_mask = DVDATrack.CHANNEL_MASK[channel_assignment]
            self.bits_per_sample = DVDATrack.BITS_PER_SAMPLE[group1_bps]
            self.stream_id = stream_id

        finally:
            aob_file.close()

    def __len__(self):
        return len(self.tracks)

    def __getitem__(self, index):
        return self.tracks[index]

    def __repr__(self):
        return "DVDATitle(%s)" % \
            (",".join(["%s=%s" % (key, getattr(self, key))
                       for key in ["titleset", "title", "pts_length",
                                   "tracks"]]))

    def info(self):
        """returns a (sample_rate, channels, channel_mask, bps, type) tuple"""

        return (self.sample_rate,
                self.channels,
                self.channel_mask,
                self.bits_per_sample,
                self.stream_id)

    def to_pcm(self):
        """returns a PCMReader-compatible object of Title data
        this PCMReader requires the use of its next_track() method
        which indicates the total number of PTS ticks to read
        from the next track in the title"""

        from audiotools.decoders import DVDA_Title

        args = {"audio_ts": self.dvdaudio.audio_ts_path,
                "titleset": 1,
                "start_sector": self.tracks[0].first_sector,
                "end_sector": self.tracks[-1].last_sector}
        if (self.dvdaudio.cdrom_device is not None):
            args["cdrom"] = self.dvdaudio.cdrom_device
        return DVDA_Title(**args)

    def total_frames(self):
        """returns the title's total PCM frames as an integer"""

        import decimal

        return int((decimal.Decimal(self.pts_length) /
                    DVDAudio.PTS_PER_SECOND *
                    self.sample_rate).quantize(
                decimal.Decimal(1),
                rounding=decimal.ROUND_UP))

    def metadata_lookup(self, musicbrainz_server="musicbrainz.org",
                        musicbrainz_port=80,
                        freedb_server="us.freedb.org",
                        freedb_port=80,
                        use_musicbrainz=True,
                        use_freedb=True):
        """generates a set of MetaData objects from DVD title

        returns a metadata[c][t] list of lists
        where 'c' is a possible choice
        and 't' is the MetaData for a given track (starting from 0)

        this will always return at least one choice,
        which may be a list of largely empty MetaData objects
        if no match can be found for the title"""

        from audiotools import metadata_lookup

        PTS_PER_FRAME = DVDAudio.PTS_PER_SECOND / 75

        offsets = [150]
        for track in self.tracks[0:-1]:
            offsets.append(offsets[-1] + (track.pts_length / PTS_PER_FRAME))

        return metadata_lookup(first_track_number=1,
                               last_track_number=len(self),
                               offsets=offsets,
                               lead_out_offset=self.pts_length / PTS_PER_FRAME,
                               total_length=self.pts_length / PTS_PER_FRAME,
                               musicbrainz_server=musicbrainz_server,
                               musicbrainz_port=musicbrainz_port,
                               freedb_server=freedb_server,
                               freedb_port=freedb_port,
                               use_musicbrainz=use_musicbrainz,
                               use_freedb=use_freedb)


class DVDATrack:
    """an object representing an individual DVD-Audio track"""

    SAMPLE_RATE = [48000, 96000, 192000, 0, 0, 0, 0, 0,
                   44100, 88200, 176400, 0, 0, 0, 0, 0]
    CHANNELS = [1, 2, 3, 4, 3, 4, 5, 3, 4, 5, 4, 5, 6, 4, 5, 4, 5, 6, 5, 5, 6]
    CHANNEL_MASK = [0x4, 0x3, 0x103, 0x33, 0xB, 0x10B, 0x3B, 0x7,
                    0x107, 0x37, 0xF, 0x10F, 0x3F, 0x107, 0x37, 0xF,
                    0x10F, 0x3F, 0x3B, 0x37, 0x3F]
    BITS_PER_SAMPLE = [16, 20, 24] + [0] * 13

    def __init__(self, dvdaudio,
                 titleset, title, track,
                 first_pts, pts_length,
                 first_sector, last_sector):
        self.dvdaudio = dvdaudio
        self.titleset = titleset
        self.title = title
        self.track = track
        self.first_pts = first_pts
        self.pts_length = pts_length
        self.first_sector = first_sector
        self.last_sector = last_sector

    def __repr__(self):
        return "DVDATrack(%s)" % \
            (", ".join(["%s=%s" % (attr, getattr(self, attr))
                        for attr in ["titleset",
                                     "title",
                                     "track",
                                     "first_pts",
                                     "pts_length",
                                     "first_sector",
                                     "last_sector"]]))

    def total_frames(self):
        """returns the track's total PCM frames as an integer

        this is based on its PTS ticks and the title's sample rate"""

        import decimal

        return int((decimal.Decimal(self.pts_length) /
                    DVDAudio.PTS_PER_SECOND *
                    self.title.sample_rate).quantize(
                decimal.Decimal(1),
                rounding=decimal.ROUND_UP))

    def sectors(self):
        """iterates (aob_file, start_sector, end_sector)

        for each AOB file necessary to extract the track's data
        in the order in which they should be read"""

        track_sectors = Rangeset(self.first_sector,
                                 self.last_sector + 1)

        for (i, (start_sector,
                 end_sector)) in enumerate(self.dvdaudio.aob_sectors):
            aob_sectors = Rangeset(start_sector, end_sector)
            intersection = aob_sectors & track_sectors
            if (len(intersection)):
                yield (self.dvdaudio.files["ATS_%2.2d_%d.AOB" % \
                                               (self.titleset, i + 1)],
                       intersection.start - start_sector,
                       intersection.end - start_sector)


class Rangeset:
    """an optimized combination of range() and set()"""

    #The purpose of this class is for finding the subset of
    #two Rangesets, such as with:
    #
    # >>> Rangeset(1, 10) & Rangeset(5, 15)
    # Rangeset(5, 10)
    #
    #which returns another Rangeset object.
    #This is preferable to performing:
    #
    # >>> set(range(1, 10)) & set(range(5, 15))
    # set([8, 9, 5, 6, 7])
    #
    #which allocates lots of unnecessary values
    #when all we're interested in is the min and max.

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return "Rangeset(%s, %s)" % (repr(self.start), repr(self.end))

    def __len__(self):
        return int(self.end - self.start)

    def __getitem__(self, i):
        if (i >= 0):
            if (i < len(self)):
                return self.start + i
            else:
                raise IndexError(i)
        else:
            if (-i - 1 < len(self)):
                return self.end + i
            else:
                raise IndexError(i)

    def __and__(self, rangeset):
        min_point = max(self.start, rangeset.start)
        max_point = min(self.end, rangeset.end)

        if (min_point <= max_point):
            return Rangeset(min_point, max_point)
        else:
            return Rangeset(0, 0)
