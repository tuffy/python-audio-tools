#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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

from audiotools._ogg import PageReader,PageWriter,Page

class PacketReader:
    def __init__(self, pagereader):
        """pagereader is a PageReader object"""

        self.__pagereader__ = pagereader
        self.__page__ = Page(packet_continuation=0,
                             stream_beginning=0,
                             stream_end=0,
                             granule_position=0,
                             bitstream_serial_number=0,
                             sequence_number=0,
                             segments=[])
        self.__current_segment__ = 1

    def read_segment(self):
        if (self.__current_segment__ >= len(self.__page__)):
            self.read_page()

        segment = self.__page__[self.__current_segment__]
        self.__current_segment__ += 1
        return segment

    def read_page(self):
        self.__page__ = self.__pagereader__.read()
        self.__current_segment__ = 0
        return self.__page__

    def read_packet(self):
        """returns next Ogg packet as a string"""

        segments = []

        segment = self.read_segment()
        segments.append(segment)
        while (len(segment) == 255):
            segment = self.read_segment()
            segments.append(segment)

        return "".join(segments)

    def close(self):
        """closes stream for further reading"""

        self.__pagereader__.close()


def packet_to_pages(packet, bitstream_serial_number,
                    starting_sequence_number=0):
    """given a string of packet data,
    yields a Page object per Ogg page necessary to hold that packet

    packet_continuation is filled in as needed
    stream_beginning and stream_end are False
    granule_position is 0
    sequence_number increments starting from "starting_sequence_number"
    """

    from audiotools._ogg import Page

    page = Page(
        packet_continuation=False,
        stream_beginning=False,
        stream_end=False,
        granule_position=0,
        bitstream_serial_number=bitstream_serial_number,
        sequence_number=starting_sequence_number,
        segments=[])

    while (len(packet) > 0):
        if (page.full()):
            yield page
            starting_sequence_number += 1
            page = Page(
                packet_continuation=True,
                stream_beginning=False,
                stream_end=False,
                granule_position=0,
                bitstream_serial_number=bitstream_serial_number,
                sequence_number=starting_sequence_number,
                segments=[])

        page.append(packet[0:255])
        packet = packet[255:]

    yield page
