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

:mod:`audiotools.dvda` --- the DVD-Audio Input/Output Module
============================================================

.. module:: audiotools.dvda
   :synopsis: a Module for Accessing DVD-Audio Data



The :mod:`audiotools.dvda` module contains a set of classes
for accessing DVD-Audio data.

DVD Objects
-----------

.. class:: DVDA(audio_ts_path, [cdrom_device])

   A DVDA object represents the entire disc.
   ``audio_ts_path`` is the path to the disc's mounted
   ``AUDIO_TS`` directory, such as ``/media/cdrom/AUDIO_TS``.
   ``cdrom_device``, if given, is the path to the device
   the disc is mounted from, such as ``/dev/cdrom``.

   If the disc is encrypted and ``cdrom_device`` is given,
   decryption will be performed automatically.

   May raise :exc:`IOError` if some error occurs opening
   the disc.

.. data:: DVDA.titlesets

   The number of title sets on the disc, typically 1.

.. method:: DVDA.titleset(titleset_number)

   Given a title set number, starting from 1,
   returns that :class:`Titleset` object.
   Raises :exc:`IndexError` if that title set is not found on the disc.

Titleset Objects
----------------

.. class:: Titleset(dvda, titleset_number)

   A Titleset object represents a title set on a disc.
   ``dvda`` is a :class:`DVDA` object and ``titleset_number``
   is the title set number.

   My raise :exc:`IndexError` if the title set is not found on the disc.

.. data:: Titleset.number

   The title set's number.

.. data:: Titleset.titles

   The number of titles in the title set.

.. method:: Titleset.title(title_number)

   Given a title number, starting from 1,
   returns that :class:`Title` object.
   Raises :exc:`IndexError` if that title is not found on the disc.

Title Objects
-------------

.. class:: Title(titleset, title_number)

   A Title object represents a title in a title set.
   ``titleset`` is a :class:`Titleset` object and ``title_number``
   is the title number.

   May raise :exc:`IndexError` if the title is not found in the title set.

.. data:: Title.number

   The title's number.

.. data:: Title.tracks

   The number of tracks in the title.

.. data:: Title.pts_length

   The length of the title in PTS ticks.
   There are 90000 PTS ticks per second.

.. method:: Title.track(track_number)

   Given a track number, starting from 1,
   returns that :class:`Track` object.
   Raises :exc:`IndexError` if that track is not found in the title.

Track Objects
-------------

.. class:: Track(title, track_number)

   A Track object represents a track in a title.
   ``title`` is a :class:`Title` object and ``track_number``
   is the track number.

   May raise :exc:`ValueError` if the track is not found in the title.

.. data:: Track.number

   The track's number.

.. data:: Track.pts_index

   The starting point of the track in the title, in PTS ticks.

.. data:: Track.pts_length

   The length of the track in PTS ticks.
   There are 90000 PTS ticks per second.

.. data:: Track.first_sector

   The track's first sector in the stream of ``.AOB`` files.
   Each sector is exactly 2048 bytes long.

.. data:: Track.last_sector

   The track's last sector in the stream of ``.AOB`` files.

.. method:: Track.reader()

   Returns a :class:`TrackReader` for reading this track's data.
   May raise :exc:`IOError` if some error occurs opening the reader.

TrackReader Objects
-------------------

.. class:: TrackReader(track)

   TrackReader is a :class:`audiotools.PCMReader` compatible object
   for extracting the audio data from a given track.
   ``track`` is a :class:`Track` object.

   May raise :exc:`IOError` if some error occurs opening the reader.

.. data:: TrackReader.sample_rate

   The track's sample rate, in Hz.

.. data:: TrackReader.bits_per_sample

   The track's bits-per-sample, either 24 or 16.

.. data:: TrackReader.channels

   The track's channel count, often 2 or 6.

.. data:: TrackReader.channel_mask

   The track's channel mask as a 32-bit value.

.. data:: TrackReader.total_pcm_frames

   The track's total number of PCM frames.

.. data:: TrackReader.codec

   The track's codec as a string.

.. method:: TrackReader.read(pcm_frames)

   Attempts to read the given number of PCM frames
   from the track as a :class:`audiotools.pcm.FrameList` object.
   May return less than the requested number of PCM frames
   at the end of the disc.

   Attempting to read from a closed stream will raise :exc:`ValueError`.

.. method:: TrackReader.close()

   Closes the stream for further reading.
