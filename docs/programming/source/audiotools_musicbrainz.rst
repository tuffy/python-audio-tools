..
  Audio Tools, a module and set of tools for manipulating audio data
  Copyright (C) 2007-2016  Brian Langenberger

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

:mod:`audiotools.musicbrainz` --- MusicBrainz Lookup Service Module
===================================================================

.. module:: audiotools.musicbrainz
   :synopsis: a Module for Accessing MusicBrainz Information

The :mod:`audiotools.musicbrainz` module contains classes
and functions for performing lookups to the MusicBrainz service.

DiscID Objects
--------------

.. class:: DiscID(first_track_number, last_track_number, lead_out_offset, offsets)

   A MusicBrainz disc ID object used to perform lookups.
   ``first_track_number`` is the first track number on the CD
   (typically 1),
   ``last_track_number`` is the last track number on the CD.
   ``lead_out_offset`` is the CD's lead-out sector offset
   (including the 2 second pre-gap).
   ``offsets`` is a list of track offsets in CD sectors
   (1/75th of a second), each including the 2 second pre-gap
   at the start of the disc.

.. method:: DiscID.__str__()

   Returns the disc ID as a 28 character string
   that MusicBrainz expects when performing lookups.

.. classmethod:: DiscID.from_cddareader(cddareader)

   Given a :class:`audiotools.cdio.CDDAReader` object,
   returns the :class:`DiscID` of that disc.

.. classmethod:: DiscID.from_tracks(tracks)

   Given a sorted list of :class:`audiotools.AudioFile` objects,
   returns the :class:`DiscID` as if those tracks were a CD.

.. warning::

   This assumes all the tracks from the disc are present
   and are laid out in a conventional
   fashion with no "hidden" tracks or other oddities.
   The disc ID may not be accurate if that's not the case.

.. classmethod:: DiscID.from_sheet(sheet, total_pcm_frames, sample_rate)

   Given a :class:`audiotools.Sheet` object along
   with the total length of the disc in PCM frames
   and the disc's sample rate (typically 44100),
   returns the :class:`DiscID`.

Performing Lookup
-----------------

.. function:: perform_lookup(disc_id, musicbrainz_server, musicbrainz_port)

   Given a :class:`DiscID` object,
   MusicBrainz hostname string and MusicBrainz server port (usually 80),
   iterates over a list of :class:`audiotools.MetaData` objects
   per successful match, like:

   ``[track1, track2, ...], [track1, track2, ...], ...``

   May yield nothing if the server has no matches for the given disc ID.

   May raise :exc:`urllib2.HTTPError` if an error occurs
   querying the server or :exc:`xml.parsers.expat.ExpatError`
   if the server returns invalid data.
