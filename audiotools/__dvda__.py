#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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


from audiotools import Con,re,os

class DVDAudio:
    """An object representing an entire DVD-Audio disc.

    A DVDAudio object contains one or more DVDATitle objects
    (accessible via the .titlesets attribute).
    Typically, only the first DVDTitle is interesting.
    Each DVDATitle then contains one or more DVDATrack objects.
    """

    SECTOR_SIZE = 2048
    PTS_PER_SECOND = 90000

    AUDIO_TS_IFO = Con.Struct(
        "AUDIO_TS_IFO",
        Con.Const(Con.Bytes("identifier", 12), "DVDAUDIO-AMG"),
        Con.UBInt32("AMG_start_sector"),
        Con.Padding(12),
        Con.UBInt32("AMGI_end_sector"),
        Con.UBInt16("DVD_version"),
        Con.Padding(4),
        Con.UBInt16("volume_count"),
        Con.UBInt16("volume_number"),
        Con.UBInt8("disc_side"),
        Con.Padding(4),
        Con.UBInt8("autoplay"),
        Con.UBInt32("ts_to_sv"),
        Con.Padding(10),
        Con.UBInt8("video_titlesets"),
        Con.UBInt8("audio_titlesets"),
        Con.Bytes("provider_identifier", 40))

    ATS_XX_S1 = Con.Struct(
        "ATS_XX",
        Con.Const(Con.String("identifier", 12), "DVDAUDIO-ATS"),
        Con.UBInt32("ATS_end_sector"),
        Con.Padding(12),
        Con.UBInt32("ATSI_end_sector"),
        Con.UBInt16("DVD_specification_version"),
        Con.UBInt32("VTS_category"),
        Con.Padding(90),
        Con.UBInt32("ATSI_MAT_end_sector"),
        Con.Padding(60),
        Con.UBInt32("VTSM_VOBS_start_sector"),
        Con.UBInt32("ATST_AOBS_start_sector"),
        Con.UBInt32("VTS_PTT_SRPT_start_sector"),
        Con.UBInt32("ATS_PGCI_UT_start_sector"),
        Con.UBInt32("VTSM_PGCI_UT_start_sector"),
        Con.UBInt32("VTS_TMAPT_start_sector"),
        Con.UBInt32("VTSM_C_ADT_start_sector"),
        Con.UBInt32("VTSM_VOBU_ADMA_start_sector"),
        Con.UBInt32("VTS_C_ADT_start_sector"),
        Con.UBInt32("VTS_VOBU_ADMAP_start_sector"),
        Con.Padding(24))

    ATS_XX_S2 = Con.Struct(
        "ATS_XX2",
        Con.UBInt16("title_count"),
        Con.Padding(2),
        Con.UBInt32("last_byte_address"),
        Con.StrictRepeater(
            lambda ctx: ctx['title_count'],
            Con.Struct('titles',
                       Con.UBInt16("unknown1"),
                       Con.UBInt16("unknown2"),
                       Con.UBInt32("byte_offset"))))

    ATS_TITLE = Con.Struct(
        "ATS_title",
        Con.Bytes("unknown1", 2),
        Con.UBInt8("tracks"),
        Con.UBInt8("indexes"),
        Con.UBInt32("track_length"),
        Con.Bytes("unknown2", 4),
        Con.UBInt16("sector_pointers_table"),
        Con.Bytes("unknown3", 2),
        Con.StrictRepeater(
            lambda ctx: ctx["tracks"],
            Con.Struct("timestamps",
                       Con.Bytes("unknown1", 2),
                       Con.Bytes("unknown2", 2),
                       Con.UBInt8("track_number"),
                       Con.Bytes("unknown3", 1),
                       Con.UBInt32("first_pts"),
                       Con.UBInt32("pts_length"),
                       Con.Padding(6))))

    ATS_SECTOR_POINTER = Con.Struct(
        "sector_pointer",
        Con.Const(Con.Bytes("unknown", 4),
                  '\x01\x00\x00\x00'),
        Con.UBInt32("first_sector"),
        Con.UBInt32("last_sector"))

    def __init__(self, audio_ts_path):
        """A DVD-A which contains PCMReader-compatible track objects."""

        #an inventory of AUDIO_TS files converted to uppercase keys
        self.files = dict([(name.upper(),
                            os.path.join(audio_ts_path, name))
                           for name in os.listdir(audio_ts_path)])

        titleset_count = self.__titleset_count__()

        #for each titleset, read an ATS_XX_0.IFO file
        #each titleset contains one or more DVDATitle objects
        #and each DVDATitle object contains one or more DVDATrack objects
        self.titlesets = [self.__titles__(titleset) for titleset in
                          xrange(1, titleset_count + 1)]

        #for each titleset, calculate the lengths of the corresponding AOBs
        #in terms of 2048 byte sectors
        self.aob_sectors = []
        for titleset in xrange(1, titleset_count + 1):
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

    def __titleset_count__(self):
        """return the number of titlesets from AUDIO_TS.IFO"""

        try:
            f = open(self.files['AUDIO_TS.IFO'], 'rb')
        except KeyError,IOError:
            raise InvalidDVDA(u"unable to open AUDIO_TS.IFO")
        try:
            try:
                return DVDAudio.AUDIO_TS_IFO.parse_stream(f).audio_titlesets
            except Con.ConstError:
                raise InvalidDVDA(u"invalid AUDIO_TS.IFO")
        finally:
            f.close()

    def __titles__(self, titleset):
        """returns a list of DVDATitle objects for the given titleset"""

        try:
            f = open(self.files['ATS_%2.2d_0.IFO' % (titleset)], 'rb')
        except KeyError,IOError:
            raise InvalidDVDA(
                u"unable to open ATS_%2.2d_0.IFO" % (titleset))
        try:
            try:
                #the first sector contains little of interest
                #but we'll read it to check the identifier string
                DVDAudio.ATS_XX_S1.parse_stream(f)
            except Con.ConstError:
                raise InvalidDVDA(u"invalid ATS_%2.2d_0.IFO" % (titleset))

            #then move to the second sector and continue parsing
            f.seek(DVDAudio.SECTOR_SIZE, os.SEEK_SET)

            #may contain one or more titles
            title_records = DVDAudio.ATS_XX_S2.parse_stream(f)

            titles = []

            for (title_number,
                 title_offset) in enumerate(title_records.titles):
                f.seek(DVDAudio.SECTOR_SIZE +
                       title_offset.byte_offset,
                       os.SEEK_SET)
                title = DVDAudio.ATS_TITLE.parse_stream(f)

                f.seek(DVDAudio.SECTOR_SIZE +
                       title_offset.byte_offset +
                       title.sector_pointers_table,
                       os.SEEK_SET)

                titles.append(DVDATitle(
                        length=title.track_length,
                        tracks=[DVDATrack(dvdaudio=self,
                                          titleset=titleset,
                                          title=title_number + 1,
                                          track=timestamp.track_number,
                                          first_pts=timestamp.first_pts,
                                          pts_length=timestamp.pts_length,
                                          first_sector=pointers.first_sector,
                                          last_sector=pointers.last_sector)
                                for (timestamp, pointers) in
                                zip(title.timestamps, [
                                    DVDAudio.ATS_SECTOR_POINTER.parse_stream(f)
                                    for i in xrange(title.tracks)])]))

            return titles


        finally:
            f.close()


class InvalidDVDA(Exception):
    pass

class DVDATitle:
    """An object representing a DVD-Audio title.

    Contains one or more DVDATrack objects
    which may are accessible via the .tracks attribute.
    """

    def __init__(self, length, tracks):
        """length is in PTS ticks, tracks is a list of DVDATrack objects"""

        self.length = length
        self.tracks = tracks

    def __repr__(self):
        return "DVDATitle(%s, %s)" % (repr(self.length), repr(self.tracks))

class DVDATrack:
    """An object representing an individual DVD-Audio track."""

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

    def sectors(self):
        """iterates (aob_file, start_sector, end_sector)

        for each AOB file necessary to extract the track's data
        in the order in which they should be read."""

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
    """An optimized combination of range() and set()"""

    #The purpose of this class is for finding the subset of
    #two Rangesets, such as with:
    #
    #>>> Rangeset(1, 10) & Rangeset(5, 15)
    #
    #which returns another Rangeset object.
    #This is preferable to performing:
    #
    #>>> set(range(1, 10)) & set(range(5, 15))
    #
    #which would allocate lots of unnecessary values.

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return "Rangeset(%s, %s)" % (repr(self.start), repr(self.end))

    def __len__(self):
        return self.end - self.start

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
