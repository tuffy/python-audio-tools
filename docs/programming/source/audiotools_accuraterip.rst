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

:mod:`audiotools.accuraterip` --- AccurateRip Lookup Service Module
===================================================================

.. module:: audiotools.accuraterip
   :synopsis: a Module for Accessing AccurateRip Information

The :mod:`audiotools.accuraterip` module contains classes
and functions for performing lookups to the AccurateRip service.

ChecksumV1 Objects
------------------

.. class:: ChecksumV1(total_pcm_frames [, sample_rate=44100][, is_first=False][, is_last=False][, pcm_frame_range=1])

   A class for calculating AccurateRip's version 1 checksum.
   ``total_pcm_frames`` is the length of the track to be checksummed.
   ``sample_rate``, ``is_first`` and ``is_last`` are used
   to calculate the checksum properly at the beginning, middle
   and end of the disc.
   ``pcm_frame_range`` is used to calculate the checksum
   over a window's worth of values.

.. note::

   The total number of PCM frames expected by ChecksumV1
   equals ``total_pcm_frames`` + ``pcm_frame_range`` - 1.
   For example, given ``total_pcm_frames`` of 100
   and a ``pcm_frame_range`` of 3,
   one will populate the :class:`ChecksumV1` object
   with 102 PCM frames and receive 3 checksum values.
   The first checksum is for ``frames[0:100]``,
   the second for ``frames[1:101]`` and the third for
   ``frames[2:102]``.

   The purpose of this is to determine whether a track has been
   ripped accurately, but its samples are simply shifted
   by some positive or negative number of samples.

.. method:: ChecksumV1.update(framelist)

   Updates the checksum in progress with the given
   :class:`audiotools.pcm.FrameList` object.
   May raise :exc:`ValueError` if too many PCM frames are given to process.

.. method:: ChecksumV1.checksums()

   Returns a list of 32-bit AccurateRip checksums, 1 per ``pcm_frame_range``.
   May raise :exc:`ValueError` if not enough PCM frames have been
   processed.

Disc ID Objects
---------------

.. class:: DiscID(track_numbers, track_offsets, lead_out_offset, freedb_disc_id)

   An AccurateRip disc ID object used to perform lookups.
   ``track_numbers`` is a list of track numbers, starting from 1.
   ``track_offsets`` is a list of track offsets in CD sectors,
   *not* including the 2 second lead-in.
   ``lead_out_offset`` is the lead-out sector of the CD,
   *not* including the 2 second lead-in.
   ``freedb_disc_id`` is a string or :class:`audiotools.freedb.DiscID`
   object of the disc's FreeDB disc ID.

.. method:: DiscID.__str__()

   Returns the disc ID as a 39 character string
   that AccurateRip expects when performing lookups.

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

.. function:: perform_lookup(disc_id[, accuraterip_server][, accuraterip_port])

   Given a :class:`DiscID` object
   and optional AccurateRip hostname string and port,
   returns a dict of

   ``{track_number:[(confidence, crc, crc2), ...], ...}``

   where ``track_number`` starts from 1,
   ``crc`` is an AccurateRip checksum integer
   and ``confidence`` is an integer of the match's confidence level.

   May return a dict of empty lists if no AccurateRip entry is found.

   May raise :exc:`urllib2.HTTPError` if an error occurs querying the server.

Determining Match Offset
------------------------

.. function:: match_offset(ar_matches, checksums, initial_offset)

   ``ar_matches`` is a dict of

   ``{track_number:[(confidence, crc, crc2), ...], ...}``

   values returned by :func:`perform_lookup`.

   ``checksums`` is a list of checksum integers returned by
   :func:`ChecksumV1.checksums()`.

   ``initial_offset`` is the initial PCM frames offset
   of the checksums (which may be negative).

   Returns a ``(checksum, confidence, offset)`` tuple
   of the best match found.
   If no matches are found, the checksum at offset 0
   is returned and ``confidence`` is ``None``.
